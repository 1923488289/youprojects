from django.shortcuts import render
from django.views import View
from django import http
from meiduo_mall.utils.response_code import RETCODE
import json
from goods.models import SKU
from django_redis import get_redis_connection
from meiduo_mall.utils import meiduo_json
from . import constants


class CartView(View):
    def post(self, request):
        '''
        加入购物车,json参数
        :param sku_id:库存商品编号
        :param count:数量
        '''
        # 1.接收
        param_dict = json.loads(request.body.decode())
        sku_id = param_dict.get('sku_id')
        count = param_dict.get('count')

        # 2.验证
        # 2.1非空
        if not all([sku_id, count]):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '参数不完整'})
        # 2.2库存商品编号有效
        try:
            sku = SKU.objects.get(pk=sku_id, is_launched=True)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号无效'})
        # 2.3数量
        try:
            count = int(count)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '数量格式错误'})
        if count <= 0:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '数量必须大于0'})
        if count > sku.stock:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '超过库存'})

        # 3.处理
        user = request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
        if user.is_authenticated:
            # 已登录，将信息保存在redis中
            redis_cli = get_redis_connection('carts')
            redis_pl = redis_cli.pipeline()
            # 向hash中添加库存商品编号、数量
            redis_pl.hset('cart%d' % user.id, sku_id, count)
            # 向set中添加库存商品编号，表示选中这个商品
            redis_pl.sadd('selected%d' % user.id, sku_id)
            # 执行交互
            redis_pl.execute()
        else:
            # 未登录，将信息保存在cookie中
            # 1.读取cookie中购物车数据
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                # 第一次向购物车中添加商品数据
                cart_dict = {}
            else:
                # cookie中已有购物车数据，转换成字典
                cart_dict = meiduo_json.loads(cart_str)
            # 2.向购物车中添加数据
            cart_dict[sku_id] = {
                'count': count,
                'selected': True
            }
            # 3.将购物车数据写入cookie中
            response.set_cookie('cart', meiduo_json.dumps(cart_dict), max_age=constants.CART_EXPIRES)

        # 4.响应
        return response

    def get(self, request):
        # 处理：
        # 1.查询购物车数据
        user = request.user
        cart_dict = {}

        if user.is_authenticated:
            # 已登录，从redis中获取购物车数据
            redis_cli = get_redis_connection('carts')
            # hash===>sku_id,count
            cart = redis_cli.hgetall('cart%d' % user.id)  # {1:2,2:3}
            # set=====>sku_id，即选中状态
            selected = redis_cli.smembers('selected%d' % user.id)  # [1,2,3]
            # 遍历，将bytes===>int
            for sku_id, count in cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in selected
                }
            '''
            {
                16:{
                    'count':1,
                    'selected':True
                },
                ...
            }
            '''
        else:
            # 未登录，从cookie中获取购物车数据
            cart_str = request.COOKIES.get('cart')
            if cart_str is not None:
                cart_dict = meiduo_json.loads(cart_str)

        # 2.查询库存商品对象
        skus = SKU.objects.filter(pk__in=cart_dict.keys(), is_launched=True)  # [15,16]

        # 3.遍历，转换成前端需要的格式
        cart_skus = []
        for sku in skus:
            count = cart_dict[sku.id]['count']
            selected = cart_dict[sku.id]['selected']
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),  # js中没有decimal类型，需要转换成字符串再输出给js
                'count': count,
                'selected': str(selected),  # js中bool类型为true或false，python中为True或False
                'total_amount': str(sku.price * count)
            })

        context = {
            'cart_skus': cart_skus
        }
        return render(request, 'cart.html', context)

    def put(self, request):
        '''
        修改购物车中的数据json
        :param sku_id:库存商品编号
        :param count:数量
        :param selected:选中状态
        '''
        # 接收
        param_dict = json.loads(request.body.decode())
        sku_id = param_dict.get('sku_id')
        count = param_dict.get('count')
        selected = param_dict.get('selected', True)

        # 验证
        # 非空，不要对bool类型进行验证
        if not all([sku_id, count]):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '参数不完整'})
        # 2.2库存商品编号有效
        try:
            sku = SKU.objects.get(pk=sku_id, is_launched=True)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号无效'})
        # 2.3数量
        try:
            count = int(count)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '数量格式错误'})
        if count <= 0:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '数量必须大于0'})
        if count > sku.stock:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '超过库存'})
        # 2.4选中状态
        if not isinstance(selected, bool):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '选中状态无效'})

        # 处理：修改
        user = request.user
        response = http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'cart_sku': {
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),
                'count': count,
                'selected': str(selected),
                'total_amount': str(sku.price * count)
            }
        })
        if user.is_authenticated:
            # 已登录，修改redis中的hash、set
            redis_cli = get_redis_connection('carts')
            redis_pl = redis_cli.pipeline()
            # 修改hash中的数量
            redis_pl.hset('cart%d' % user.id, sku_id, count)
            # 修改set的选中状态
            if selected:
                redis_pl.sadd('selected%d' % user.id, sku_id)
            else:
                redis_pl.srem('selected%d' % user.id, sku_id)
            redis_pl.execute()
        else:
            # 未登录，修改cookie
            # 1.读取cookie中购物车数据
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '当前没有购物车数据'})
            cart_dict = meiduo_json.loads(cart_str)
            # 2.修改
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 3.写cookie
            response.set_cookie('cart', meiduo_json.dumps(cart_dict), max_age=constants.CART_EXPIRES)

        # 响应
        return response

    def delete(self, request):
        '''
        删除购物车记录
        :param sku_id:库存商品编号
        '''
        # 接收
        param_dict = json.loads(request.body.decode())
        sku_id = param_dict.get('sku_id')

        # 验证
        if not all([sku_id]):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '参数不完整'})
        # 2.2库存商品编号有效
        try:
            sku = SKU.objects.get(pk=sku_id, is_launched=True)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号无效'})

        # 处理:删除
        user = request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok'})
        if user.is_authenticated:
            # 已登录，则删除redis中的hash、set
            redis_cli = get_redis_connection('carts')
            redis_pl = redis_cli.pipeline()
            # 删除hash
            redis_pl.hdel('cart%d' % user.id, sku_id)
            # 删除set
            redis_pl.srem('selected%d' % user.id, sku_id)
            redis_pl.execute()
        else:
            # 未登录，则删除cookie中记录
            # 1.读取cookie中购物车数据
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '购物车无效'})
            cart_dict = meiduo_json.loads(cart_str)
            # 2.删除指定的库存商品
            if sku_id in cart_dict:
                del cart_dict[sku_id]
            # 3.写cookie
            response.set_cookie('cart', meiduo_json.dumps(cart_dict), max_age=constants.CART_EXPIRES)

        # 响应
        return response


class CartSelectView(View):
    def put(self, request):
        '''
        设置购物车中的商品选中状态，要么全选中，要么全不选中
        :param selected:选中状态，True，False
        '''
        # 接收
        param_dict = json.loads(request.body.decode())
        selected = param_dict.get('selected', True)

        # 验证
        if not isinstance(selected, bool):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '选中状态无效'})

        # 处理
        user = request.user
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': "ok"})
        if user.is_authenticated:
            # 已登录，修改set中的值
            redis_cli = get_redis_connection('carts')
            if selected:
                # 读取hash中所有库存商品编号
                sku_ids = redis_cli.hkeys('cart%d' % user.id)  # [1,2,3,4]===>1,2,3,4
                # 如果选中，则将所有库存商品编号加入集合
                redis_cli.sadd('selected%d' % user.id, *sku_ids)
            else:
                # 如果不选中，则将集合中所有的库存商品编号删除
                redis_cli.delete('selected%d' % user.id)
        else:
            # 未登录，修改cookie中的值
            # 1.读取cookie中购物车数据
            cart_str = request.COOKIES.get('cart')
            if cart_str is None:
                return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '购物车无效'})
            cart_dict = meiduo_json.loads(cart_str)
            # 2.遍历字典，修改selected属性
            for sku_id, dict1 in cart_dict.items():
                dict1['selected'] = selected
            # 3.写cookie
            response.set_cookie('cart', meiduo_json.dumps(cart_dict), max_age=constants.CART_EXPIRES)

        # 响应
        return response


class CartSimpleView(View):
    def get(self, request):
        # 读取购物车数据，做出简单提示
        user = request.user
        cart_dict = {}
        # 1.查询购物车数据
        if user.is_authenticated:
            redis_cli = get_redis_connection('carts')
            cart_dict = redis_cli.hgetall('cart%d' % user.id)
            cart_dict = {int(sku_id): int(count) for sku_id, count in cart_dict.items()}
            '''
            {
                库存商品编号1：数量1,
                库存商品编号2：数量2,
                ...
            }
            '''
        else:
            cart_str = request.COOKIES.get('cart')
            if cart_str is not None:
                '''
                {
                    库存商品编号1:{
                        'count':数量,
                        'selected':选中状态
                    },
                    ....
                }
                '''
                cart_dict = meiduo_json.loads(cart_str)
                # 将字典结构统一
                cart_dict = {sku_id: cart['count'] for sku_id, cart in cart_dict.items()}
        # 2.查询库存商品对象，转换成前端需要的格式
        skus = SKU.objects.filter(pk__in=cart_dict.keys(), is_launched=True)
        sku_list = []
        for sku in skus:
            sku_list.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'count': cart_dict[sku.id]
            })
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': '',
            'cart_skus': sku_list
        })
