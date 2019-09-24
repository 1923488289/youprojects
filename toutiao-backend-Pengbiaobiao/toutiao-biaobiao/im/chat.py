"""socketIO框架"""

from server import sio
import time


@sio.on('connect')
def on_connect(sid, environ):
    """
    与客户端建立好连接后被执行
    :param sid: string sid是socketio为当前连接客户端生成的识别id
    :param environ: dict 在连接握手时客户端发送的握手数据(HTTP报文解析之后的字典)
    """
    # sio.emit(消息事件类型， 消息数据内容， 接收人)

    # 与前端约定好, 聊天的内容 数据格式
    data = {
        'msg': 'hello',
        'timestamp': round(time.time() * 1000)
    }

    # 与前端约定好，聊天的内容数据都定义为message类型
    sio.emit('message', data, room=sid)
    # sio.send(data, room=sid)


@sio.on("message")
def on_message(sid, data):
    """
    与前端约定好，前端发送的聊天数据事件类型也是message类型
    :param sid: string sid是发送此事件消息的客户端id
    :param data: data是客户端发送的消息数据
      与前端约定好 前端发送的数据格式也是
      {
        "msg": xx,
        "timestamp": xxx
      }
    :return:
    """
    # TODO 此处使用rpc调用聊天机器人子系统 获取聊天回复内容

    resp_data = {
        "msg": 'I have received your msg: {}'.format(data.get('msg')),
        "timestamp": round(time.time() * 1000)
    }
    # sio.emit('message', resp_data, room=sid)
    sio.send(resp_data, room=sid)
