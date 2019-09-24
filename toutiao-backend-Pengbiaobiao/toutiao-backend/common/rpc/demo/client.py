import grpc
import time

import reco_pb2_grpc
import reco_pb2


def run():
    """
    客户端调用运行
    :return:
    """
    # 与rpc服务器建立连接
    with grpc.insecure_channel('127.0.0.1:8888') as channel:
        # 创建用户进行rpc调用的工具
        stub = reco_pb2_grpc.UserRecommendStub(channel)

        # 进行rpc调用
        req = reco_pb2.UserRequest()
        req.user_id = '1'
        req.channel_id = 12
        req.article_num = 10
        req.time_stamp = round(time.time() * 1000)

        ret = stub.user_recommend(req)
        # ret -> ArticleResponse 对象
        print('ret={}'.format(ret))



if __name__ == '__main__':
    run()