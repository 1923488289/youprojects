from flask import g, current_app
from functools import wraps
from sqlalchemy.orm import load_only
from sqlalchemy.exc import SQLAlchemyError

from models import db


def set_db_to_read(func):
    """
    设置使用读数据库
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        db.session().set_to_read()
        return func(*args, **kwargs)

    return wrapper


def set_db_to_write(func):
    """
    设置使用写数据库
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        db.session().set_to_write()
        return func(*args, **kwargs)

    return wrapper


def login_required(func):
    def wrapper(*args, **kwargs):
        if g.user_id is not None and g.use_refresh_token is False:
            return func(*args, **kwargs)
        else:
            # abort(401)
            return {'message':'Invalid token'}, 401
    return wrapper


def validate_token_if_using(func):
    """
    如果Authorization中携带了Token，则检验token的有效性，否则放行
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if g.use_token and not g.user_id:
            return {'message': 'Token has some errors.'}, 401
        else:
            if g.user_id:
                # 判断用户状态
                user_enable = cache_user.UserStatusCache(g.user_id).get()
                if not user_enable:
                    return {'message': 'User denied.'}, 403

            return func(*args, **kwargs)

    return wrapper
