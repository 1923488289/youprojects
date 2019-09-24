from flask import request, g
from utils.jwt_util import verify_jwt


def jwt_authentication():
    """校验token的请求钩子"""

    g.user_id = None
    g.use_refresh_token = False

    # 从请求头中获取token
    # token格式：Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1NjA4NDc0MzMsInVzZXJfaWQiOjExNDA4NzI3NDQ1NDAzMDc0NTZ9.50upsAE1XqD3wxbRZuVmqmDZ6F3iO6wtTumEqeq3OUY
    token = request.headers.get('Authorization')

    if token is not None and token.startswith('Bearer '):
        token = token[7:]
        payload = verify_jwt(token)
        if payload is not None:
            g.user_id = payload.get('user_id')

            # 如果时refresh_token
            g.use_refresh_token=payload.get("is_refresh", False)

