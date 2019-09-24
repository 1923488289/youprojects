from flask import current_app
from qiniu import Auth, put_file, etag, put_data


def upload(file_data):
    """
    上传文件到七牛
    :param:file_data从客户端接受的文件数据
    """
    # 需要填写你的 Access Key 和 Secret Key
    access_key = current_app.config['QINIU_ACCESS_KEY']
    secret_key = current_app.config['QINIU_SECRET_KEY']
    # 构建鉴权对象
    q = Auth(access_key, secret_key)
    # 要上传的空间
    bucket_name = current_app.config['QINIU_BUCKET_NAME']
    # 上传后保存的文件名
    key = None
    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600000)

    # 要上传文件的本地路径
    # localfile = './sync/bbb.jpg'
    # ret, info = put_file(token, key, localfile)
    # flask从客户端接受的文件已经暂存在内存中，是一个文件对象
    ret, info = put_data(token, key, file_data)

    print('ret={}'.format(ret))
    print('info={}'.format(info))

    return ret['key']


"""
image_file = open('/home/python/TouTiaoWeb/toutiao-biaobiao/imgs/2268548648.jpg','rb')
image_data = image_file.read()
sys.path.extend(['/home/python/TouTiaoWeb/toutiao-biaobiao'])
from toutiao.main import app
from utils.qiniu_storage import upload
with app.app_context():
    upload(image_data)
    
ret={'hash': 'Fo8mfz7Elz0t_cLwFOdJfuJHIw3q', 'key': 'Fo8mfz7Elz0t_cLwFOdJfuJHIw3q'}
info=_ResponseInfo__response:<Response [200]>, exception:None, status_code:200, text_body:{"hash":"Fo8mfz7Elz0t_cLwFOdJfuJHIw3q","key":"Fo8mfz7Elz0t_cLwFOdJfuJHIw3q"}, req_id:NBcAAADKdB0nxqsV, x_log:X-Log
"""

"""上传文件存储地址：http://ptp58xrrk.bkt.clouddn.com/Fo8mfz7Elz0t_cLwFOdJfuJHIw3q"""
