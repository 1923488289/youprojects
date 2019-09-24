from flask import current_app
from redis.exceptions import RedisError
from models import db
from models.news import Article
from sqlalchemy import func
from models.user import Relation

#  count:user:arts   ->   zset
#                         成员值     分数score
#                         user_id   文章数量
#                         user_1      100
#                         user_2      3
#                         user_3      36


class CountStorageBase(object):
    """数量存储工具父类"""

    key = ''

    @classmethod
    def get(cls, id):
        """查询指定用户的文章数量"""
        try:
            count = current_app.redis_master.zscore(cls.key, id)
        except RedisError as e:
            current_app.logger.error(e)
            count = current_app.redis_slave.zscore(cls.key, id)
        return 0 if count is None else int(count)

    @classmethod
    def increase(cls, id, increment):
        """累加用户的文章数量"""
        try:
            current_app.redis_master.zincrby(cls.key, increment, id)
        except RedisError as e:
            current_app.logger.error(e)
            raise e

    @classmethod
    def reset(cls, db_query_result):
        """重置redis记录"""
        r = current_app.redis_master

        r.delete(cls.key)

        redis_data = []
        for user_id, count in db_query_result:
            redis_data.append(count)
            redis_data.append(user_id)

        r.zadd(cls.key, *redis_data)

    @staticmethod
    def db_query():
        """用于修正redis数据的查询"""
        pass


class UserArticlesCountStorage(CountStorageBase):
    """用户文章数量工具类"""

    key = 'counter:user:arts'

    @staticmethod
    def db_query():
        return db.session.query(Article.user_id, func.count(Article.id)).filter(
            Article.status == Article.STATUS.APPROVED).group_by(Article.user_id).all()


class UserFollowingsCountStorage(CountStorageBase):
    """用户关注数量工具类"""

    key = 'count:user:follows'

    @staticmethod
    def db_query():
        return db.session.query(Relation.user_id, func.count(Relation.target_user_id)).filter(
            Relation.relation == Relation.RELATION.FOLLOW).group_by(Relation.user_id).all()


class UserFansCountStorage(CountStorageBase):
    """用户粉丝数量工具类"""

    key = 'count:user:fans'


class UserLikingCountStorage(CountStorageBase):
    """用户点赞数量工具类"""

    key = 'count:user:liking'


class ArticleCollectingCountStorage(CountStorageBase):
    """文章收藏数量工具类"""

    key = 'count:art:collecting'
