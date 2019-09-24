from flask import current_app
from redis.exceptions import RedisError
from sqlalchemy import func

from models import db
from models.news import Article, Collection, Attitude, CommentLiking, Comment
from models.user import Relation

# # 用户文章数量
# #  count:user:arts   ->   zset
# #                         成员值     分数score
# #                         user_id   文章数量
# #                         user_1     100
# #                         user_2      3
# #                         user_3     36
#
#
# # 需求 （用法）
# #   1  查
# #   2  累计数据
#
#
# class UserArticlesCountStorage(object):
#     """
#     用户文章数量存储工具类
#     """
#
#     key = 'count:user:arts'
#
#     @classmethod
#     def get(cls, user_id):
#         """
#         查询指定用户的文章数量
#         :param user_id:
#         :return:
#         """
#         # r = current_app.redis_master
#         # r.zscore()
#
#         try:
#             count = current_app.redis_master.zscore(cls.key, user_id)
#         except RedisError as e:
#             current_app.logger.error(e)
#             count = current_app.redis_slave.zscore(cls.key, user_id)
#
#         return 0 if count is None else int(count)
#
#     @classmethod
#     def increase(cls, user_id, increment=1):
#         """
#         累计用户的文章数量
#         :param user_id:
#         :param increment: 累计值 可正数可负数
#         :return:
#         """
#         try:
#             current_app.redis_master.zincrby(cls.key, increment, user_id)
#         except RedisError as e:
#             current_app.logger.error(e)
#             raise e
#
#
#
#
# # UserArticlesCountStorage.get(user_id)
#
#
# # UserArticlesCountStorage.increase(user_id, -3)
# # UserArticlesCountStorage.increase(user_id)
#
#
# # 用户粉丝数量   zset  user_id 成员 粉丝数量 score
# # 用户关注数量
# # 点赞数量
# # 文章收藏量  zset   成员 article_Id  score 收藏数量


#################### 考虑到其他的统计数据 redis的使用与用户文章数 相同，所以可复用代码 ###############################


class CountStorageBase(object):
    """
    数量存储工具类父类
    """

    key = ''

    @classmethod
    def get(cls, member_id):
        """
        查询
        :param member_id:
        :return:
        """
        # r = current_app.redis_master
        # r.zscore()

        try:
            count = current_app.redis_master.zscore(cls.key, member_id)
        except RedisError as e:
            current_app.logger.error(e)
            count = current_app.redis_slave.zscore(cls.key, member_id)

        return 0 if count is None else int(count)

    @classmethod
    def incr(cls, member_id, increment=1):
        """
        累计
        :param member_id:
        :param increment: 累计值 可正数可负数
        :return:
        """
        try:
            current_app.redis_master.zincrby(cls.key, increment, member_id)
        except RedisError as e:
            current_app.logger.error(e)
            raise e

    @classmethod
    def reset(cls, db_query_result):
        """
        重置redis数据
        :return:
        """
        # 删除redis的记录
        r = current_app.redis_master

        r.delete(cls.key)

        # 将数据库的数据保存到redis中
        # #  count:user:arts   ->   zset
        # #                         成员值     分数score
        # #                         user_id   文章数量
        # #                         user_1     100
        # #                         user_2      3
        # #                         user_3     36
        # zadd key score member
        # 方式一：
        # pl = r.pipeline()
        # for user_id, count in ret:
        #     pl.zadd(key, count, user_id)
        # pl.execute()

        # 方式二
        # zadd key score1 member1 score2 member2 ...
        # r.zadd(key, count1, user_1, count2, user_2, ....)

        redis_data = []
        for user_id, count in db_query_result:
            redis_data.append(count)
            redis_data.append(user_id)

        # redis_data -> [count1, user_1, count2, user2, ,...]
        r.zadd(cls.key, *redis_data)

        # ** 解字典
        # * 解列表或元祖

    @staticmethod
    def db_query():
        """
        用户修正redis数据的数据库查询方法
        :return:
        """
        pass


class UserArticlesCountStorage(CountStorageBase):
    """
    用户文章数量工具类
    """
    key = 'count:user:arts'

    @staticmethod
    def db_query():
        return db.session.query(Article.user_id, func.count(Article.id)).filter(
            Article.status == Article.STATUS.APPROVED) \
            .group_by(Article.user_id).all()


# 用户发布文章的接口中 会累计用户文章数量
# POST  /articles
# 强制用户登录
# 视图处理流程：
#   1. 接收数据
#   2. 检验参数
#   3. 保存文章的数据库数据 MySQL
#   4. UserArticlesCountStorage.increase(g.user_id)  Redis
#   5. 返回
#
# 这里存在一个"分布式事务" 但是重要性不高
# 数据库保存文章数据成功，但是有可能redis累加数据出现偏差，因为redis中保存的累计数据相比文章的数据库数据重要性弱，所以以保存数据库
# 数据为主，允许redis在平时累计数据的时候 出现偏差，可以依赖定时任务 查询数据库 统计数据 进行纠偏。


class UserFollowingsCountStorage(CountStorageBase):
    """
    用户关注数量工具类
    """
    key = 'count:user:follows'

    @staticmethod
    def db_query():
        # select user_id, count(target_user_id) from user_relation where relation=1 group by user_id
        return db.session.query(Relation.user_id, func.count(Relation.target_user_id))\
            .filter(Relation.relation == Relation.RELATION.FOLLOW).group_by(Relation.user_id).all()


class ArticleReadingCountStorage(CountStorageBase):
    """
    文章阅读量
    """
    key = 'count:art:reading'


class UserArticlesReadingCountStorage(CountStorageBase):
    """
    作者的文章阅读总量
    """
    kye = 'count:user:arts:reading'


class ArticleCollectingCountStorage(CountStorageBase):
    """
    文章收藏数量
    """
    key = 'count:art:collecting'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Collection.article_id, func.count(Collection.article_id)) \
            .filter(Collection.is_deleted == 0).group_by(Collection.article_id).all()
        return ret


class UserArticleCollectingCountStorage(CountStorageBase):
    """
    用户收藏数量
    """
    key = 'count:user:art:collecting'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Collection.user_id, func.count(Collection.article_id)) \
            .filter(Collection.is_deleted == 0).group_by(Collection.user_id).all()
        return ret


class ArticleDislikeCountStorage(CountStorageBase):
    """
    文章不喜欢数据
    """
    key = 'count:art:dislike'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Attitude.article_id, func.count(Collection.article_id)) \
            .filter(Attitude.attitude == Attitude.ATTITUDE.DISLIKE).group_by(Collection.article_id).all()
        return ret


class ArticleLikingCountStorage(CountStorageBase):
    """
    文章点赞数据
    """
    key = 'count:art:liking'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Attitude.article_id, func.count(Collection.article_id)) \
            .filter(Attitude.attitude == Attitude.ATTITUDE.LIKING).group_by(Collection.article_id).all()
        return ret


class CommentLikingCountStorage(CountStorageBase):
    """
    评论点赞数据
    """
    key = 'count:comm:liking'

    @classmethod
    def db_query(cls):
        ret = db.session.query(CommentLiking.comment_id, func.count(CommentLiking.comment_id)) \
            .filter(CommentLiking.is_deleted == 0).group_by(CommentLiking.comment_id).all()
        return ret


class ArticleCommentCountStorage(CountStorageBase):
    """
    文章评论数量
    """
    key = 'count:art:comm'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Comment.article_id, func.count(Comment.id)) \
            .filter(Comment.status == Comment.STATUS.APPROVED).group_by(Comment.article_id).all()
        return ret


class CommentReplyCountStorage(CountStorageBase):
    """
    评论回复数量
    """
    key = 'count:art:reply'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Comment.parent_id, func.count(Comment.id)) \
            .filter(Comment.status == Comment.STATUS.APPROVED, Comment.parent_id != None)\
            .group_by(Comment.parent_id).all()
        return ret


class UserFollowersCountStorage(CountStorageBase):
    """
    用户粉丝数量
    """
    key = 'count:user:followers'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Relation.target_user_id, func.count(Relation.user_id)) \
            .filter(Relation.relation == Relation.RELATION.FOLLOW) \
            .group_by(Relation.target_user_id).all()
        return ret


class UserLikedCountStorage(CountStorageBase):
    """
    用户被赞数量
    """
    key = 'count:user:liked'

    @classmethod
    def db_query(cls):
        ret = db.session.query(Article.user_id, func.count(Attitude.id)).join(Attitude.article) \
            .filter(Attitude.attitude == Attitude.ATTITUDE.LIKING) \
            .group_by(Article.user_id).all()
        return ret



