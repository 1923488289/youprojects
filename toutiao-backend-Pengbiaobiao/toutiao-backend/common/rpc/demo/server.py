import grpc
from concurrent.futures import ThreadPoolExecutor
import time

import reco_pb2_grpc
import reco_pb2


class UserRecommendServicer(reco_pb2_grpc.UserRecommendServicer):
    """
    实现被调用的方法
    """

    def user_recommend(self, request, context):
        """
        用户文章推荐 实际是由推荐系统编写
        :param request: rpc调用的请求数据对象  UserRequest对象
        :param context: 如果被调用的这个方法出现了异常，可以通过context提供的方法来告知rpc调用的一方错误信息
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details('Method not implemented!')
        :return:
        """
        # 获取rpc调用的请求参数
        user_id = request.user_id
        channel_id = request.channel_id
        article_num = request.article_num
        time_stamp = request.time_stamp

        # 为了看到效果 先伪推荐
        # 构建调用返回值对象
        response = reco_pb2.ArticleResponse()
        response.exposure = 'exposure param'
        response.time_stamp = round(time.time() * 1000)

        articles_list = []
        for i in range(article_num):
            article = reco_pb2.Article()
            article.article_id = i + 1
            article.track.click = 'click param '
            article.track.collect = 'collect param '
            article.track.share = 'share param '
            article.track.read = 'read param '
            articles_list.append(article)

        # response.recommends.append(Article())
        # 注意 在grpc中 不使用append方法 使用extend
        response.recommends.extend(articles_list)

        return response



def serve():
    """
    RPC服务器运行程序，启动后可以等待接收rpc的调用请求
    """
    # 创建RPC服务器对象
    server = grpc.server(ThreadPoolExecutor(max_workers=10))

    # 将RPC的具体函数代码 交给RPC服务器对象
    # reco_pb2_grpc.add_UserRecommendServicer_to_server(业务代码, server)
    reco_pb2_grpc.add_UserRecommendServicer_to_server(UserRecommendServicer(), server)

    # 为服务器绑定ip地址和端口号
    server.add_insecure_port('127.0.0.1:8888')

    # 启动服务器运行
    server.start()  # 非阻塞方法

    # 为了不让程序退出
    while True:
        time.sleep(10)


if __name__ == '__main__':
    serve()