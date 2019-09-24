"""socketIO服务器"""

import eventlet
eventlet.monkey_patch()

import socketio
import eventlet.wsgi
import sys
from server import app
import chat
import notify

# sys.argv 列表，保存了程序启动的命令行参数
# python main.py 8000
# sys.argv -> ['main.py', '8000']
if len(sys.argv) < 2:
    print('Usage: python main.py [port].')
    exit(1)

port = int(sys.argv[1])


# 创建eventlet服务器对象
SERVER_ADDRESS = ('0.0.0.0', port)
listen_sock = eventlet.listen(SERVER_ADDRESS)
eventlet.wsgi.server(listen_sock, app)
