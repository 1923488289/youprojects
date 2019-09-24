#coding=utf-8

"""RPC服务器"""
import time
import grpc
import reco_pb2
import reco_pb2_grpc
from concurrent.futures import ThreadPoolExecutor


class UserRcommendServicer(reco_pb2_grpc.UserRcommendServicer):
    """推荐系统"""

    def user_recommend(self, request, context):
        """
        伪造推荐系统
        :param request: rpc调用的请求数据对象 UserRequest对象
        :param context: 给予程序上下文环境，主要用于返回异常
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details('Method not implemented!')
        :return:
        """
        # 获取rpc调用的请求参数
        user_id = request.user_id
        channel_id = request.channel_id
        article_num = request.article_num
        time_stamp = request.time_stamp

        # 伪造推荐系统返回对象ArticleResponse
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


def server():
    """
    RPC服务器运行程序，启动后等待接受rpc的调用请求
    :return:
    """
    # 创建RPC服务器
    server = grpc.server(ThreadPoolExecutor(max_workers=10))

    # 将RPC业务代码补全交给RPC服务器对象
    reco_pb2_grpc.add_UserRcommendServicer_to_server(UserRcommendServicer(), server)

    # 为服务器绑定IP地址
    server.add_insecure_port('127.0.0.1:8888')

    # 启动服务器运行
    server.start()  # 非阻塞的运行

    # 手动阻塞，防止服务器推出
    while True:
        time.sleep(3)


if __name__ == '__main__':
    server()
