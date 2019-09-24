from qiniu import Auth, put_file, etag, put_data
import qiniu.config
from flask import current_app


def upload(file_data):
    """
    上传文件到七牛
    :param file_data: 接收的客户端携带的图片数据
    :return:
    """
    # 需要填写你的 Access Key 和 Secret Key
    access_key = current_app.config['QINIU_ACCESS_KEY']
    secret_key = current_app.config['QINIU_SECRET_KEY']

    # 构建鉴权对象
    q = Auth(access_key, secret_key)

    # 要上传的空间
    bucket_name = current_app.config['QINIU_BUCKET_NAME']

    # 上传后保存的文件名
    # 由七牛自己生成
    key = None

    # 生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600000)

    #要上传文件的本地路径
    # localfile = './sync/bbb.jpg'
    # ret, info = put_file(token, key, localfile)

    # flask从客户端中接收的文件已经暂存在内存中，是一个文件对象，可以直接读取文件对象的数据
    # 所以此处更适用于直接使用put_data方法，将文件数据上传到七牛
    ret, info = put_data(token, key, file_data)

    print('ret={}'.format(ret))
    print('info={}'.format(info))

    # ret = {'hash': 'FqJDeg56KWUkGpjwgv3okRCoimi7', 'key': 'FqJDeg56KWUkGpjwgv3okRCoimi7'}
    # info = _ResponseInfo__response: < Response[200] >, exception: None, status_code: 200, text_body: {
    #     "hash": "FqJDeg56KWUkGpjwgv3okRCoimi7",
    #     "key": "FqJDeg56KWUkGpjwgv3okRCoimi7"}, req_id: lKAAAAAAe7L2tKsV, x_log: X - Log
    return ret['key']  # 七牛保存的文件名称