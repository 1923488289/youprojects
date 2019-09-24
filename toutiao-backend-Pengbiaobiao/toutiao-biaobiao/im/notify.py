from server import sio
from werkzeug.wrappers import Request
import jwt

# 密钥需要与flask密钥相同
JWT_SECRET = 'TPmi4aLWRbyVq8zu9v82dWYW17/z+UvRnYTt4P6fAXA'


def verify_jwt(token, secret=None):
    """
    检验jwt
    :param token: jwt
    :param secret: 密钥
    :return: dict: payload
    """
    try:
        payload = jwt.decode(token, secret, algorithm=['HS256'])
    except jwt.PyJWTError:
        payload = None

    return payload


@sio.on('connect')
def on_connect(sid, environ):
    """
    与客户端建立好连接后被执行
    :param sid: string sid是socketio为当前连接客户端生成的识别id
    :param environ: dict 在连接握手时客户端发送的握手数据(HTTP报文解析之后的字典)
    """
    # 前端链接socketio服务器时 携带的查询字符串中包含的token 是随着第一次websocket握手的http报文携带
    # 可以通过environ取出

    # 借助werkzeug 工具集 来帮助我们解读 客户度请求的hTTP数据
    request = Request(environ)

    # 对于解读出来的request对象，可以像在flask中使用一样来读取数据
    token = request.args.get('token')

    if token is not None:
        payload = verify_jwt(token, JWT_SECRET)
        if payload is not None:
            user_id = payload.get('user_id')

            # 将用户加入用户id名称的房间
            sio.enter_room(sid, str(user_id))


@sio.on('disconnect')
def on_disconnect(sid):
    """
    客户端断开连接的时候
    :return:
    """
    # 查询sid存在的房间rooms 列表
    rooms = sio.rooms(sid)

    for room in rooms:
        # 将用户移除房间
        sio.leave_room(sid, room)
