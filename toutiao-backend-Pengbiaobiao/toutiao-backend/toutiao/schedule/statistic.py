from cache import statistic as cache_statistic


# def fix_statistics(flask_app):
#     """
#     修正统计数据的定时任务函数
#     :return:
#     """
#     # 因为这个函数是被scheduler对象 在独立于视图执行流程之外，单独在子线程中计时，定时执行，与flask视图执行无关
#     # 所以如果用到上下文对象，没有了flask 视图的支持，需要自己创建上下文环境，才能使用current_app
#
#     with flask_app.app_context():
#
#         # 用户文章数量
#         # 查询数据库 获取统计数据
#         # select user_id, count(article_id) from news_article_basic where status=2 group by user_id
#         ret = db.session.query(Article.user_id, func.count(Article.id)).filter(
#             Article.status == Article.STATUS.APPROVED) \
#             .group_by(Article.user_id).all()
#         # +---------+-------------------+
#         # | user_id | count(article_id) |
#         # +---------+-------------------+
#         # |       1 |             46141 |
#         # |       2 |             46357 |
#         # |       3 |             46187 |
#         # |       5 |                25 |
#         # +---------+-------------------+
#         # ret -> [(1, 46141), (2, 46357), ....]
#
#         # redis数据重置
#         # 删除redis的记录
#         r = current_app.redis_master
#         key = 'count:user:arts'
#         r.delete(key)
#
#         # 将数据库的数据保存到redis中
#         # #  count:user:arts   ->   zset
#         # #                         成员值     分数score
#         # #                         user_id   文章数量
#         # #                         user_1     100
#         # #                         user_2      3
#         # #                         user_3     36
#         # zadd key score member
#         # 方式一：
#         # pl = r.pipeline()
#         # for user_id, count in ret:
#         #     pl.zadd(key, count, user_id)
#         # pl.execute()
#
#         # 方式二
#         # zadd key score1 member1 score2 member2 ...
#         # r.zadd(key, count1, user_1, count2, user_2, ....)
#
#         redis_data = []
#         for user_id, count in ret:
#             redis_data.append(count)
#             redis_data.append(user_id)
#
#         # redis_data -> [count1, user_1, count2, user2, ,...]
#         r.zadd(key, *redis_data)
#
#         # ** 解字典
#         # * 解列表或元祖


def __fix_process(storage_tool_class):
    ret = storage_tool_class.db_query()
    storage_tool_class.reset(ret)


def fix_statistics(flask_app):
    """
    修正统计数据的定时任务函数
    :return:
    """
    # 因为这个函数是被scheduler对象 在独立于视图执行流程之外，单独在子线程中计时，定时执行，与flask视图执行无关
    # 所以如果用到上下文对象，没有了flask 视图的支持，需要自己创建上下文环境，才能使用current_app

    with flask_app.app_context():

        # 用户文章数量
        __fix_process(cache_statistic.UserArticlesCountStorage)

        # 用户关注数量
        __fix_process(cache_statistic.UserFollowingsCountStorage)



