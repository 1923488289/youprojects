from flask import request, g
from utils.jwt_util import verify_jwt


def jwt_authentication():
    """
    检验token的请求钩子函数
    :return:
    """
    g.user_id = None
    g.use_refresh_token = False
    g.use_token = False

    # 从请求头中取token
    token = request.headers.get('Authorization')

    # Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1NjA4NDc0MzMsInVzZXJfaWQiOjExNDA4NzI3NDQ1NDAzMDc0NTZ9.50upsAE1XqD3wxbRZuVmqmDZ6F3iO6wtTumEqeq3OUY

    if token is not None and token.startswith('Bearer '):
        g.use_token = True
        token = token[7:]
        # 校验token
        payload = verify_jwt(token)
        if payload is not None:
            g.user_id = payload.get('user_id')

            # 如果是刷新token
            g.use_refresh_token = payload.get("is_refresh", False)




    # # if 已登录用户，用户有身份信息
    # g.user_id = 123
    # # else 未登录用户，用户无身份信息
    # # g.user_id = None