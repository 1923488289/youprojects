import socketio

# 由于不启动flask服务测试，就直接把数据拿过来用了
RABBITMQ = 'amqp://python:rabbitmqpwd@localhost:5672/toutiao'

# 创建socketIO.manager对象，以便socketIO从中间件提取数据
# mgr = socketio.KombuManager(current_app.config['RABBITMQ'])
mgr = socketio.KombuManager(RABBITMQ)

# 创建socketIO对象
# async_mode 告知socketio 服务器使用eventlet 协程服务器来托管运行
sio = socketio.Server(async_mode='eventlet',client_manager=mgr)
app = socketio.Middleware(sio)
