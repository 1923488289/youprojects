import pickle
import base64


def dumps(param_dict):
    '''
    将字典转换成字符串
    '''
    # 1.将字典转字节
    dict_bytes = pickle.dumps(param_dict)
    # 2.将字节转码
    str_bytes = base64.b64encode(dict_bytes)
    # 3.将字节转字符串
    return str_bytes.decode()


def loads(param_str):
    '''
    将字符串转换成字典
    '''
    # 1.将字符串转字节
    str_bytes = param_str.encode()
    # 2.将字节转码
    dict_bytes = base64.b64decode(str_bytes)
    # 3.将字节转字典
    return pickle.loads(dict_bytes)
