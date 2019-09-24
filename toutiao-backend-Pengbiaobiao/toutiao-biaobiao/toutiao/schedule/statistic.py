from cache import statistic as cache_statistic


def __fix_process(storage_tool_class):
    ret = storage_tool_class.db_query()
    storage_tool_class.reset(ret)


def fix_statistic(flask_app):
    """修正统计数据的定时任务"""

    with flask_app.app_context():

        # 用户文章数量统计修正
        # 查询 mysql 数据库
        # select user_id, count(article_id) from new_article_basic where status=2 group by user_id
        # ret = cache_statistic.UserArticlesCountStorage.db_query()
        # redis 数据重置
        # cache_statistic.UserArticlesCountStorage.reset(ret)
        __fix_process(cache_statistic.UserArticlesCountStorage)

        # 用户关注数量统计修正
        # ret = cache_statistic.UserFollowingsCountStorage.db_query()
        # cache_statistic.UserArticlesCountStorage.reset(ret)
        __fix_process(cache_statistic.UserFollowingsCountStorage)
