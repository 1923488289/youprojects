"""RPC客户端程序"""
import time
import grpc
import reco_pb2
import reco_pb2_grpc


def run():
    """客户端运行函数"""

    # 与rpc服务器建立连接
    with grpc.insecure_channel('127.0.0.1:8888') as channel:

        # 创建用户调用rpc调用的工具
        stub = reco_pb2_grpc.UserRcommendStub(channel)

        # 进行rpc调用(实际使用过程中应该从前端拿到参数)
        req = reco_pb2.UserRequest()
        req.user_id = '1'
        req.channel_id = 12
        req.article_num = 10
        req.time_stamp = round(time.time() * 1000)

        ret = stub.user_recommend(req)
        # ret 保存获得的 ArticleResponse 对象
        print('ret={}'.format(ret))


if __name__ == '__main__':
    run()
