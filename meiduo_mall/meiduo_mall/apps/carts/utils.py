from meiduo_mall.utils import meiduo_json
from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, response):
    #以cookie中的数据为准，如果cookie与redis中有同一个库存商品，则使用cookie中的数据覆盖redis中的数据
    user = request.user
    # 1.读取cookie中购物车数据
    cart_str = request.COOKIES.get('cart')
    if cart_str is None:
        return response
    cart_dict = meiduo_json.loads(cart_str)
    '''
    {
        库存商品编号：{
            'count':数量,
            'selected':True或False
        },
        ....
    }
    '''

    # 2.存入redis中
    redis_cli = get_redis_connection('carts')
    redis_pl = redis_cli.pipeline()
    # 遍历字典，逐个转存
    for sku_id, cart in cart_dict.items():
        # hash
        redis_pl.hset('cart%d' % user.id, sku_id, cart['count'])
        # set
        if cart['selected']:
            redis_pl.sadd('selected%d' % user.id, sku_id)
        else:
            redis_pl.srem('selected%d' % user.id, sku_id)
    redis_pl.execute()

    # 3.删除cookie中购物车数据
    response.delete_cookie('cart')
    return response
