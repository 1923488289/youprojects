from django.shortcuts import render
from django.views import View
from .models import GoodsCategory, SKU, GoodsVisitCount
from meiduo_mall.utils.category import get_category
from django.core.paginator import Paginator
from django import http
from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.breadcrumb import get_breadcrumb
from .models import SKUSpecification
from datetime import datetime
import json
from django_redis import get_redis_connection
from celery_tasks.detail.tasks import generate_static_detail_html


class ListView(View):
    def get(self, request, category_id, page_num):
        # 查询当前指定的分类对象
        try:
            category3 = GoodsCategory.objects.get(pk=category_id)
        except:
            return render(request, '404.html')

        # 分类
        categories = get_category()

        # 面包屑导航
        breadcrumb = get_breadcrumb(category3)

        # 热销排行(后续通过Ajax实现)

        # 当前分类的库存商品
        skus = category3.sku_set.filter(is_launched=True)
        # 排序
        sort = request.GET.get('sort', 'default')
        if sort == 'price':
            # 价格
            skus = skus.order_by('price')
        elif sort == 'hot':
            # 人气
            skus = skus.order_by('-sales')
        else:
            # 默认
            skus = skus.order_by('-id')
        # 分页
        paginator = Paginator(skus, 5)  # 将列表skus按照每页5条数据进行分页
        page_skus = paginator.page(page_num)  # 获取第page_num页的数据
        total_page = paginator.num_pages  # 总页数

        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sort': sort,
            'page_skus': page_skus,
            'category': category3,
            'page_num': page_num,
            'total_page': total_page
        }

        return render(request, 'list.html', context)


class HotView(View):
    def get(self, request, category_id):
        # 查询指定分类的2个热销商品
        hots = SKU.objects.filter(is_launched=True, category_id=category_id).order_by('-sales')[0:2]

        # 转换成字典
        hot_list = []
        for hot in hots:
            hot_list.append({
                'id': hot.id,
                'name': hot.name,
                'default_image_url': hot.default_image.url,
                'price': hot.price
            })

        # 响应json
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'hot_sku_list': hot_list
        })


class DetailView(View):
    def get(self, request, sku_id):
        generate_static_detail_html.delay(sku_id)

        try:
            sku = SKU.objects.get(pk=sku_id)
        except:
            return render(request, '404.html')

        # - 频道分类
        categories = get_category()

        # 面包屑导航
        category3 = sku.category
        breadcrumb = get_breadcrumb(category3)

        # - 库存商品对象(根据主键查询)

        # 标准商品对象
        spu = sku.spu

        # - 规格选项
        # 当前库存商品的选项，如当前库存商品为15号，则当前规格选项信息为：[16,20]===>6,7
        # list1=sku.specs.order_by('spec_id')
        # option_current=[]
        # for info in list1:
        #     option_current.append(info.option_id)
        option_current = [info.option_id for info in sku.specs.order_by('spec_id')]

        # 查询所有的库存商品与选项信息
        skus = spu.sku_set.filter(is_launched=True)
        '''
        当前数据，需要包含：库存商品编号，选项列表
        当前已知：选项列表，找：库存商品编号
        {
            选项列表：库存商品编号
        }
        dict1[键]===>值
        '''
        sku_option_dict = {}
        for sku_temp in skus:
            option_list = [info.option_id for info in sku_temp.specs.order_by('spec_id')]
            sku_option_dict[tuple(option_list)] = sku_temp.id
        '''
        {
            (13,20):9,
            (13,21):10,
            ...
        }
        '''

        # 规格==》选项===》链接
        # 查询指定标准商品的所有规格
        specs = spu.specs.all()  # 6===>0,7=====>1
        spec_list = []
        for index, spec in enumerate(specs):  # [20,5,8,39]
            spec_dict = {
                'name': spec.name,
                'options': []
            }
            # 查询指定规格的所有选项
            options = spec.options.all()
            # 遍历，加入规格字典的列表中
            for option in options:
                # 根据当前选项获取新的完整选项，即保持其它规格的选项不变，只替换本规格的选项
                option_current_temp = option_current[:]
                option_current_temp[index] = option.id  # [16,20]==>[13,20]===>16--->13
                sku_id = sku_option_dict.get(tuple(option_current_temp), 0)

                spec_dict['options'].append({
                    'name': option.value,
                    'selected': option.id in option_current,
                    'sku_id': sku_id
                })

            spec_list.append(spec_dict)

        # - 热销排行

        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'spu': spu,
            'category_id': category3.id,
            'spec_list': spec_list
        }
        return render(request, 'detail.html', context)


class DetailVisitView(View):
    def post(self, request, category_id):
        # 处理：
        # 查询指定三级分类当天的访问量
        try:
            now = datetime.now()
            date = '%d-%d-%d' % (now.year, now.month, now.day)
            visit = GoodsVisitCount.objects.get(category_id=category_id, date=date)
        except:
            # 如果未查询到则新建
            GoodsVisitCount.objects.create(category_id=category_id, count=1)
        else:
            # 如果查询到则修改访问量，+1
            visit.count += 1
            visit.save()
        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok'
        })


class HistoryView(View):
    def post(self, request):
        # 接收
        sku_id = json.loads(request.body.decode()).get('sku_id')

        # 验证
        # 非空
        if not all([sku_id]):
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号不能为空'})
        # 有效性
        try:
            sku = SKU.objects.get(pk=sku_id)
        except:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '库存商品编号无效'})
        # 用户验证
        user = request.user
        if not user.is_authenticated:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '用户未登录'})

        # 处理
        redis_cli = get_redis_connection('history')
        redis_pl = redis_cli.pipeline()
        key = 'history%d' % user.id
        # 1.删除列表中指定元素
        redis_pl.lrem(key, 0, sku_id)
        # 2.加入第一个
        redis_pl.lpush(key, sku_id)
        # 3.限制个数
        redis_pl.ltrim(key, 0, 4)
        # 执行redis操作
        redis_pl.execute()

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok'
        })

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return http.JsonResponse({'code': RETCODE.PARAMERR, 'errmsg': '用户未登录'})
        # 查询redis浏览记录
        redis_cli = get_redis_connection('history')
        sku_ids = redis_cli.lrange('history%d' % user.id, 0, -1)
        # bytes===>int
        sku_ids = [int(sku_id) for sku_id in sku_ids]

        # 查询库存商品对象
        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(pk=sku_id)
            # 转换成前前端需要的格式
            skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image.url,
                'name': sku.name,
                'price': sku.price
            })

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'skus': skus
        })
