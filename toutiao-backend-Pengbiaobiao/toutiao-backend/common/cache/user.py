from flask import current_app, g
import json
import time
from sqlalchemy.orm import load_only
# from rediscluster.exceptions import
from redis.exceptions import RedisError
from sqlalchemy.exc import DatabaseError

from models.user import User, Relation, UserProfile
from models.news import Article, Collection, Attitude, CommentLiking, Comment
from . import constants
from cache import statistic as cache_statistic

# 用户资料缓存数据
# key                       值
# user:{user_id}:profile   str  json  pickle
# user:1:profile           str

# 需求：
#   1. 查询用户资料数据
#   2. 清理用户资料数据缓存
#   3. 判断用户是否存在


# 设计类
# 属性 -> 数据     对象属性  类属性
#   区别： 对象属性 类的每个对象独有 不共享 不同
#         类属性   类的所有对象 共享  相同
#
# 方法 -> 对于数据的处理函数   对象方法  类方法  静态方法
#   区别：方法能够使用的数据（属性）不同
#       1. 对象方法 实例方法
#           def obj_func(self, ...)  self. 可以读写对象属性，可以读取类属性
#       2. 类方法
#           @classmethod
#           def class_func(cls, ...)  cls. 只能读写类属性
#       3. 静态方法
#           @staticmethod
#           def static_func(..)     可以通过类名读写类属性

class UserProfileCache(object):
    """
    用户资料缓存数据工具类
    """
    def __init__(self, user_id):
        # key 表示这个工具需要操作的redis键名
        self.key = 'user:{}:profile'.format(user_id)
        self.user_id = user_id

    def save(self):
        """
        查询数据库 保存缓存数据
        :return:
        """
        r = current_app.redis_cluster  # redis  cluster 连接的客户端对象
        try:
            user = User.query.options(load_only(
                User.mobile,
                User.name,
                User.profile_photo,
                User.introduction,
                User.certificate
            )).filter_by(id=self.user_id).first()
        except DatabaseError as e:
            current_app.logger.error(e)
            # 因为已经无法查到数据 数据库出现异常 所以不能返回一个有效数据 工具类也不能私自决定如何处理，所以一个原则就是继续抛出异常，交由
            # 调用者（视图）来决定如何处理这个异常
            raise e

        if user is not None:
            # 如果数据库查到数据
            # user_dict = {
            #     'mobile': user.mobile,
            #     'name': user.name,
            #     'photo': user.profile_photo,
            #     'intro': user.introduction,
            #     'certi': user.certificate
            # }
            user_dict = dict(
                mobile=user.mobile,
                name=user.name,
                photo=user.profile_photo,
                intro=user.introduction,
                certi=user.certificate
            )
            user_json = json.dumps(user_dict)

            # 保存到redis中，
            # r.setex(键， 有效期， 值)
            # 缓存雪崩
            try:
                r.setex(self.key, constants.UserProfileCacheTTL.get_val(), user_json)
            except RedisError as e:
                current_app.logger.error(e)

            # 返回
            return user_dict
        else:
            # 如果数据库没有查到数据， 为了防护缓存穿透 保存redis记录（-1），返回
            try:
                r.setex(self.key, constants.UserNotExistsCacheTTL.get_val(), -1)
            except RedisError as e:
                current_app.logger.error(e)

            return None

    def get(self):
        """
        查询用户资料数据
        :return: dict  None
        """
        r = current_app.redis_cluster  # redis  cluster 连接的客户端对象

        # 查询redis的缓存数据  redis cluster
        try:
            ret = r.get(self.key)
        except RedisError as e:
            # 记录日志
            current_app.logger.error(e)
            # 虽然redis出现异常，但是还可以挽回 从数据库中尝试查询数据，为了从数据库查询数据，所以设置ret=None，让代码进入数据库查询
            ret = None

        # python3 从redis中取出redis 字符串类型的数据 对应到python中是bytes类型  # ret -> bytes类型
        if ret is not None:
            # 如果redis中查询到数据，返回
            if ret == b'-1':  # 以b''字符串来定义bytes类型
                # 表示用户不存在
                return None
            else:
                # 表示用户存在, 取出了用户的缓存数据 json字符串
                # json.loads 可以接收bytes类型
                user_dict = json.loads(ret)

                if not user_dict['photo']:
                    user_dict['photo'] = constants.DEFAULT_USER_PROFILE_PHOTO
                user_dict['photo'] = current_app.config['QINIU_DOMAIN'] + user_dict['photo']

                return user_dict
        else:
            # 如果redis中没查到，查询数据库
            user_dict = self.save()

            if not user_dict['photo']:
                user_dict['photo'] = constants.DEFAULT_USER_PROFILE_PHOTO
            user_dict['photo'] = current_app.config['QINIU_DOMAIN'] + user_dict['photo']

            return user_dict


    def clear(self):
        """
        清除缓存数据
        :return:
        """
        # 删除redis记录
        r = current_app.redis_cluster  # redis  cluster 连接的客户端对象
        try:
            r.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)

    def exists(self):
        """
        判断用户是否存在
        :return: bool
        """
        # 查询redis记录
        r = current_app.redis_cluster  # redis  cluster 连接的客户端对象

        try:
            ret = r.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret is not None:
            # 如果redis存在数据， 返回
            if ret == b'-1':
                # 表示用户不存在
                return False
            else:
                return True
        else:
            # 如果redis不存在数据，查询数据库, 顺带形成缓存数据
            result = self.save()
            if result is None:
                return False
            else:
                return True


# user1 = UserProfileCache(1)   # 'user:{user_id}:profile'-> 'user:1:profile'
# user2 = UserProfileCache(2)   # 'user:{user_id}:profile'-> 'user:2:profile'

class UserStatusCache(object):
    """
    用户状态缓存
    """
    def __init__(self, user_id):
        self.key = 'user:{}:status'.format(user_id)
        self.user_id = user_id

    def save(self, status):
        """
        设置用户状态缓存
        :param status:
        """
        try:
            current_app.redis_cluster.setex(self.key, constants.UserStatusCacheTTL.get_val(), status)
        except RedisError as e:
            current_app.logger.error(e)

    def get(self):
        """
        获取用户状态
        :return:
        """
        rc = current_app.redis_cluster

        try:
            status = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            status = None

        if status is not None:
            return status
        else:
            user = User.query.options(load_only(User.status)).filter_by(id=self.user_id).first()
            if user:
                self.save(user.status)
                return user.status
            else:
                return False


class UserAdditionalProfileCache(object):
    """
    用户附加资料缓存（如性别、生日等）
    """
    def __init__(self, user_id):
        self.key = 'user:{}:profilex'.format(user_id)
        self.user_id = user_id

    def get(self):
        """
        获取用户的附加资料（如性别、生日等）
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.get(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            return json.loads(ret)
        else:
            profile = UserProfile.query.options(load_only(UserProfile.gender, UserProfile.birthday)) \
                .filter_by(id=self.user_id).first()
            profile_dict = {
                'gender': profile.gender,
                'birthday': profile.birthday.strftime('%Y-%m-%d') if profile.birthday else ''
            }
            try:
                rc.setex(self.key, constants.UserAdditionalProfileCacheTTL.get_val(), json.dumps(profile_dict))
            except RedisError as e:
                current_app.logger.error(e)
            return profile_dict

    def clear(self):
        """
        清除用户的附加资料
        :return:
        """
        try:
            current_app.redis_cluster.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)


class UserFollowingCache(object):
    """
    用户关注缓存数据
    """
    def __init__(self, user_id):
        self.key = 'user:{}:following'.format(user_id)
        self.user_id = user_id

    def get(self):
        """
        获取用户的关注列表
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.zrevrange(self.key, 0, -1)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            # In order to be consistent with db data type.
            return [int(uid) for uid in ret]

        # 为了防止缓存击穿，先尝试从缓存中判断关注数是否为0，若为0不再查询数据库
        ret = cache_statistic.UserFollowingsCountStorage.get(self.user_id)
        if ret == 0:
            return []

        ret = Relation.query.options(load_only(Relation.target_user_id, Relation.utime)) \
            .filter_by(user_id=self.user_id, relation=Relation.RELATION.FOLLOW) \
            .order_by(Relation.utime.desc()).all()

        followings = []
        cache = []
        for relation in ret:
            followings.append(relation.target_user_id)
            cache.append(relation.utime.timestamp())
            cache.append(relation.target_user_id)

        if cache:
            try:
                pl = rc.pipeline()
                pl.zadd(self.key, *cache)
                pl.expire(self.key, constants.UserFollowingsCacheTTL.get_val())
                results = pl.execute()
                if results[0] and not results[1]:
                    rc.delete(self.key)
            except RedisError as e:
                current_app.logger.error(e)

        return followings

    def determine_follows_target(self, target_user_id):
        """
        判断用户是否关注了目标用户
        :param target_user_id: 被关注的用户id
        :return:
        """
        followings = self.get()

        return int(target_user_id) in followings

    def update(self, target_user_id, timestamp, increment=1):
        """
        更新用户的关注缓存数据
        :param target_user_id: 被关注的目标用户
        :param timestamp: 关注时间戳
        :param increment: 增量
        :return:
        """
        rc = current_app.redis_cluster

        # Update user following user id list
        try:
            ttl = rc.ttl(self.key)
            if ttl > constants.ALLOW_UPDATE_FOLLOW_CACHE_TTL_LIMIT:
                if increment > 0:
                    rc.zadd(self.key, timestamp, target_user_id)
                else:
                    rc.zrem(self.key, target_user_id)
        except RedisError as e:
            current_app.logger.error(e)


class UserRelationshipCache(object):
    """
    用户关系缓存数据
    """

    def __init__(self, user_id):
        self.key = 'user:{}:relationship'.format(user_id)
        self.user_id = user_id

    def get(self):
        """
        获取用户的关系数据
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.hgetall(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            # 为了防止缓存击穿
            if b'-1' in ret:
                return {}
            else:
                # In order to be consistent with db data type.
                return {int(uid): int(relation) for uid, relation in ret.items()}

        ret = Relation.query.options(load_only(Relation.target_user_id, Relation.utime, Relation.relation)) \
            .filter(Relation.user_id == self.user_id, Relation.relation != Relation.RELATION.DELETE) \
            .order_by(Relation.utime.desc()).all()

        relations = {}
        for relation in ret:
            relations[relation.target_user_id] = relation.relation

        pl = rc.pipeline()
        try:
            if relations:
                pl.hmset(self.key, relations)
                pl.expire(self.key, constants.UserFollowingsCacheTTL.get_val())
            else:
                pl.hmset(self.key, {-1: -1})
                pl.expire(self.key, constants.UserRelationshipNotExistsCacheTTL.get_val())
            results = pl.execute()
            if results[0] and not results[1]:
                rc.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)

        return relations

    def determine_follows_target(self, target_user_id):
        """
        判断用户是否关注了目标用户
        :param target_user_id: 被关注的用户id
        :return:
        """
        relations = self.get()

        return relations.get(target_user_id) == Relation.RELATION.FOLLOW

    def determine_blacklist_target(self, target_user_id):
        """
        判断是否已拉黑目标用户
        :param target_user_id:
        :return:
        """
        relations = self.get()

        return relations.get(target_user_id) == Relation.RELATION.BLACKLIST

    def clear(self):
        """
        清除
        """
        current_app.redis_cluster.delete(self.key)


class UserFollowersCache(object):
    """
    用户粉丝缓存
    """
    def __init__(self, user_id):
        self.key = 'user:{}:fans'.format(user_id)
        self.user_id = user_id

    def get(self):
        """
        获取用户的粉丝列表
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.zrevrange(self.key, 0, -1)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            # In order to be consistent with db data type.
            return [int(uid) for uid in ret]

        ret = cache_statistic.UserFollowersCountStorage.get(self.user_id)
        if ret == 0:
            return []

        ret = Relation.query.options(load_only(Relation.user_id, Relation.utime))\
            .filter_by(target_user_id=self.user_id, relation=Relation.RELATION.FOLLOW)\
            .order_by(Relation.utime.desc()).all()

        followers = []
        cache = []
        for relation in ret:
            followers.append(relation.user_id)
            cache.append(relation.utime.timestamp())
            cache.append(relation.user_id)

        if cache:
            try:
                pl = rc.pipeline()
                pl.zadd(self.key, *cache)
                pl.expire(self.key, constants.UserFansCacheTTL.get_val())
                results = pl.execute()
                if results[0] and not results[1]:
                    rc.delete(self.key)
            except RedisError as e:
                current_app.logger.error(e)

        return followers

    def update(self, target_user_id, timestamp, increment=1):
        """
        更新粉丝数缓存
        """
        rc = current_app.redis_cluster
        try:
            ttl = rc.ttl(self.key)
            if ttl > constants.ALLOW_UPDATE_FOLLOW_CACHE_TTL_LIMIT:
                if increment > 0:
                    rc.zadd(self.key, timestamp, target_user_id)
                else:
                    rc.zrem(self.key, target_user_id)
        except RedisError as e:
            current_app.logger.error(e)


class UserReadingHistoryStorage(object):
    """
    用户阅读历史
    """
    def __init__(self, user_id):
        self.key = 'user:{}:his:reading'.format(user_id)
        self.user_id = user_id

    def save(self, article_id):
        """
        保存用户阅读历史
        :param article_id: 文章id
        :return:
        """
        try:
            pl = current_app.redis_master.pipeline()
            pl.zadd(self.key, time.time(), article_id)
            pl.zremrangebyrank(self.key, 0, -1*(constants.READING_HISTORY_COUNT_PER_USER+1))
            pl.execute()
        except RedisError as e:
            current_app.logger.error(e)

    def get(self, page, per_page):
        """
        获取阅读历史
        """
        r = current_app.redis_master
        try:
            total_count = r.zcard(self.key)
        except ConnectionError as e:
            r = current_app.redis_slave
            total_count = r.zcard(self.key)

        article_ids = []
        if total_count > 0 and (page - 1) * per_page < total_count:
            try:
                article_ids = r.zrevrange(self.key, (page - 1) * per_page, page * per_page - 1)
            except ConnectionError as e:
                current_app.logger.error(e)
                article_ids = current_app.redis_slave.zrevrange(self.key, (page - 1) * per_page, page * per_page - 1)

        return total_count, article_ids


class UserSearchingHistoryStorage(object):
    """
    用户搜索历史
    """
    def __init__(self, user_id):
        self.key = 'user:{}:his:searching'.format(user_id)
        self.user_id = user_id

    def save(self, keyword):
        """
        保存用户搜索历史
        :param keyword: 关键词
        :return:
        """
        pl = current_app.redis_master.pipeline()
        pl.zadd(self.key, time.time(), keyword)
        pl.zremrangebyrank(self.key, 0, -1*(constants.SEARCHING_HISTORY_COUNT_PER_USER+1))
        pl.execute()

    def get(self):
        """
        获取搜索历史
        """
        try:
            keywords = current_app.redis_master.zrevrange(self.key, 0, -1)
        except ConnectionError as e:
            current_app.logger.error(e)
            keywords = current_app.redis_slave.zrevrange(self.key, 0, -1)

        keywords = [keyword.decode() for keyword in keywords]
        return keywords

    def clear(self):
        """
        清除
        """
        current_app.redis_master.delete(self.key)


class UserArticlesCache(object):
    """
    用户文章缓存
    """
    def __init__(self, user_id):
        self.user_id = user_id
        self.key = 'user:{}:art'.format(user_id)

    def get_page(self, page, per_page):
        """
        获取用户的文章列表
        :param page: 页数
        :param per_page: 每页数量
        :return: total_count, [article_id, ..]
        """
        rc = current_app.redis_cluster

        try:
            pl = rc.pipeline()
            pl.zcard(self.key)
            pl.zrevrange(self.key, (page - 1) * per_page, page * per_page)
            total_count, ret = pl.execute()
        except RedisError as e:
            current_app.logger.error(e)
            total_count = 0
            ret = []

        if total_count > 0:
            # Cache exists.
            return total_count, [int(aid) for aid in ret]
        else:
            # No cache.
            total_count = cache_statistic.UserArticlesCountStorage.get(self.user_id)
            if total_count == 0:
                return 0, []

            ret = Article.query.options(load_only(Article.id, Article.ctime)) \
                .filter_by(user_id=self.user_id, status=Article.STATUS.APPROVED) \
                .order_by(Article.ctime.desc()).all()

            articles = []
            cache = []
            for article in ret:
                articles.append(article.id)
                cache.append(article.ctime.timestamp())
                cache.append(article.id)

            if cache:
                try:
                    pl = rc.pipeline()
                    pl.zadd(self.key, *cache)
                    pl.expire(self.key, constants.UserArticlesCacheTTL.get_val())
                    results = pl.execute()
                    if results[0] and not results[1]:
                        rc.delete(self.key)
                except RedisError as e:
                    current_app.logger.error(e)

            total_count = len(articles)
            page_articles = articles[(page - 1) * per_page:page * per_page]

            return total_count, page_articles

    def clear(self):
        """
        清除
        """
        rc = current_app.redis_cluster
        rc.delete(self.key)


class UserArticleCollectionsCache(object):
    """
    用户收藏文章缓存
    """
    def __init__(self, user_id):
        self.user_id = user_id
        self.key = 'user:{}:art:collection'.format(user_id)

    def get_page(self, page, per_page):
        """
        获取用户的文章列表
        :param page: 页数
        :param per_page: 每页数量
        :return: total_count, [article_id, ..]
        """
        rc = current_app.redis_cluster

        try:
            pl = rc.pipeline()
            pl.zcard(self.key)
            pl.zrevrange(self.key, (page - 1) * per_page, page * per_page)
            total_count, ret = pl.execute()
        except RedisError as e:
            current_app.logger.error(e)
            total_count = 0
            ret = []

        if total_count > 0:
            # Cache exists.
            return total_count, [int(aid) for aid in ret]
        else:
            # No cache.
            total_count = cache_statistic.UserArticleCollectingCountStorage.get(self.user_id)
            if total_count == 0:
                return 0, []

            ret = Collection.query.options(load_only(Collection.article_id, Collection.utime)) \
                .filter_by(user_id=self.user_id, is_deleted=False) \
                .order_by(Collection.utime.desc()).all()

            collections = []
            cache = []
            for collection in ret:
                collections.append(collection.article_id)
                cache.append(collection.utime.timestamp())
                cache.append(collection.article_id)

            if cache:
                try:
                    pl = rc.pipeline()
                    pl.zadd(self.key, *cache)
                    pl.expire(self.key, constants.UserArticleCollectionsCacheTTL.get_val())
                    results = pl.execute()
                    if results[0] and not results[1]:
                        rc.delete(self.key)
                except RedisError as e:
                    current_app.logger.error(e)

            total_count = len(collections)
            page_articles = collections[(page - 1) * per_page:page * per_page]

            return total_count, page_articles

    def clear(self):
        """
        清除
        """
        current_app.redis_cluster.delete(self.key)

    def determine_collect_target(self, target):
        """
        判断用户是否收藏了指定文章
        :param target:
        :return:
        """
        total_count, collections = self.get_page(1, -1)
        return target in collections


class UserArticleAttitudeCache(object):
    """
    用户文章态度缓存数据
    """

    def __init__(self, user_id):
        self.key = 'user:{}:art:attitude'.format(user_id)
        self.user_id = user_id

    def get_all(self):
        """
        获取用户文章态度数据
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.hgetall(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            # 为了防止缓存击穿
            if b'-1' in ret:
                return {}
            else:
                # In order to be consistent with db data type.
                return {int(aid): int(attitude) for aid, attitude in ret.items()}

        ret = Attitude.query.options(load_only(Attitude.article_id, Attitude.attitude)) \
            .filter(Attitude.user_id == self.user_id, Attitude.attitude != None).all()

        attitudes = {}
        for atti in ret:
            attitudes[atti.article_id] = atti.attitude

        pl = rc.pipeline()
        try:
            if attitudes:
                pl.hmset(self.key, attitudes)
                pl.expire(self.key, constants.UserArticleAttitudeCacheTTL.get_val())
            else:
                pl.hmset(self.key, {-1: -1})
                pl.expire(self.key, constants.UserArticleAttitudeNotExistsCacheTTL.get_val())
            results = pl.execute()
            if results[0] and not results[1]:
                rc.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)

        return attitudes

    def get_article_attitude(self, article_id):
        """
        获取指定文章态度
        :param article_id:
        :return:
        """
        if hasattr(g, 'article_attitudes'):
            attitudes = g.article_attitudes
        else:
            attitudes = self.get_all()
            g.article_attitudes = attitudes

        return attitudes.get(article_id, -1)

    def determine_liking_article(self, article_id):
        """
        判断是否对文章点赞
        :param article_id:
        :return:
        """
        return self.get_article_attitude(article_id) == Attitude.ATTITUDE.LIKING

    def clear(self):
        """
        清除
        """
        current_app.redis_cluster.delete(self.key)


class UserCommentLikingCache(object):
    """
    用户评论点赞缓存数据
    """

    def __init__(self, user_id):
        self.key = 'user:{}:comm:liking'.format(user_id)
        self.user_id = user_id

    def get(self):
        """
        获取用户文章评论点赞数据
        :return:
        """
        rc = current_app.redis_cluster

        try:
            ret = rc.smembers(self.key)
        except RedisError as e:
            current_app.logger.error(e)
            ret = None

        if ret:
            # 为了防止缓存击穿
            if b'-1' in ret:
                return []
            else:
                # In order to be consistent with db data type.
                return set([int(cid) for cid in ret])

        ret = CommentLiking.query.options(load_only(CommentLiking.comment_id)) \
            .filter(CommentLiking.user_id == self.user_id, CommentLiking.is_deleted == False).all()

        cids = [com.comment_id for com in ret]
        pl = rc.pipeline()
        try:
            if cids:
                pl.sadd(self.key, *cids)
                pl.expire(self.key, constants.UserCommentLikingCacheTTL.get_val())
            else:
                pl.sadd(self.key, -1)
                pl.expire(self.key, constants.UserCommentLikingNotExistsCacheTTL.get_val())
            results = pl.execute()
            if results[0] and not results[1]:
                rc.delete(self.key)
        except RedisError as e:
            current_app.logger.error(e)

        return set(cids)

    def determine_liking_comment(self, comment_id):
        """
        判断是否对文章点赞
        :param comment_id:
        :return:
        """
        if hasattr(g, self.key):
            liking_comments = getattr(g, self.key)
        else:
            liking_comments = self.get()
            setattr(g, self.key, liking_comments)

        return comment_id in liking_comments

    def clear(self):
        """
        清除
        """
        current_app.redis_cluster.delete(self.key)


def get_user_articles(user_id):
    """
    获取用户的所有文章列表 已废弃
    :param user_id:
    :return:
    """
    r = current_app.redis_cli['user_cache']
    timestamp = time.time()

    ret = r.zrevrange('user:{}:art'.format(user_id), 0, -1)
    if ret:
        r.zadd('user:art', timestamp, user_id)
        return [int(aid) for aid in ret]

    ret = r.hget('user:{}'.format(user_id), 'art_count')
    if ret is not None and int(ret) == 0:
        return []

    ret = Article.query.options(load_only(Article.id, Article.ctime))\
        .filter_by(user_id=user_id, status=Article.STATUS.APPROVED)\
        .order_by(Article.ctime.desc()).all()

    articles = []
    cache = []
    for article in ret:
        articles.append(article.id)
        cache.append(article.ctime.timestamp())
        cache.append(article.id)

    if cache:
        pl = r.pipeline()
        pl.zadd('user:art', timestamp, user_id)
        pl.zadd('user:{}:art'.format(user_id), *cache)
        pl.execute()

    return articles










