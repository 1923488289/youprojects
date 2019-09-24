from django.contrib.auth.backends import ModelBackend
import re
from users.models import User


class MeiduoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # username变量的值，可能是用户名，也可能是手机号，需要判断后再查询
        try:
            if re.match('^1[3-9]\d{9}$', username):
                # 手机号
                user = User.objects.get(mobile=username)
            else:
                # 用户名
                user = User.objects.get(username=username)
        except:
            # 用户名或手机号错误
            return None
        else:
            # 对比密码
            if user.check_password(password):
                return user
            else:
                return None
