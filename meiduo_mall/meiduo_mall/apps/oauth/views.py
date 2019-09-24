from django.shortcuts import render, redirect
from django.views import View
from django import http
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings

from carts.utils import merge_cart_cookie_to_redis
from meiduo_mall.utils.response_code import RETCODE
from .models import OAuthQQUser
from meiduo_mall.utils import meiduo_signature
from . import constants
from users.models import User
from django.contrib.auth import login


class QQurlView(View):
    def get(self, request):
        # 生成授权地址
        next_url = request.GET.get('next')
        # 1.创建工具对象
        qq_tool = OAuthQQ(
            settings.QQ_CLIENT_ID,
            settings.QQ_CLIENT_SECRET,
            settings.QQ_REDIRECT_URI,
            next_url
        )
        # 2.调用方法，生成url地址
        login_url = qq_tool.get_qq_url()

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'login_url': login_url
        })


class QQopenidView(View):
    def get(self, request):
        # 获取openid
        # 1.接收code
        code = request.GET.get('code')
        next_url = request.GET.get('state')

        # 2.创建工具对象
        qq_tool = OAuthQQ(
            settings.QQ_CLIENT_ID,
            settings.QQ_CLIENT_SECRET,
            settings.QQ_REDIRECT_URI,
            next_url
        )

        try:
            # 3.根据code获取token
            token = qq_tool.get_access_token(code)

            # 4.根据token获取openid
            openid = qq_tool.get_open_id(token)

            # 绑定：与本网站的账号关联
            try:
                qquser = OAuthQQUser.objects.get(openid=openid)
            except:
                # 未找到绑定对象，说明是初次授权，展示绑定页面
                # 加密
                token = meiduo_signature.dumps({'openid': openid}, constants.OPENID_EXPIRES)
                # 展示页面
                context = {'token': token}
                return render(request, 'oauth_callback.html', context)
            else:
                # 查找到绑定对象，则状态保持
                login(request, qquser.user)
                response = redirect(next_url)
                response.set_cookie('username', qquser.user.username)

                # 合并购物车
                response = merge_cart_cookie_to_redis(request, response)

                return response

        except:
            openid = 0

        return http.HttpResponse(openid)

    def post(self, request):
        # 接收用户填写的数据，进行绑定
        # 接收
        token = request.POST.get('access_token')
        mobile = request.POST.get('mobile')
        pwd = request.POST.get('pwd')
        sms_code = request.POST.get('sms_code')

        next_url = request.GET.get('state')

        # 验证：非空，格式，短信验证码，与注册相同，不再重复
        # 解密openid
        json = meiduo_signature.loads(token, constants.OPENID_EXPIRES)
        if json is None:
            return http.HttpResponseBadRequest('授权信息已经过期')
        openid = json.get('openid')

        # 处理
        # 1.根据手机号查询用户对象
        try:
            user = User.objects.get(mobile=mobile)
        except:
            # 2.如果未查询到对象，则新建用户对象
            user = User.objects.create_user(username=mobile, password=pwd, mobile=mobile)
        else:
            # 3.如果查询到用户对象，则判断密码
            if not user.check_password(pwd):
                # 3.1如果密码错误，则提示
                return http.HttpResponseBadRequest('账号信息无效')
                # 3.2如果密码正确则得到用户对象

        # 4.绑定：创建OAuthQQUser对象
        OAuthQQUser.objects.create(user=user, openid=openid)

        # 5.状态保持
        login(request, user)
        response = redirect(next_url)
        response.set_cookie('username', user.username, max_age=60 * 60 * 24 * 14)

        # 合并购物车
        response = merge_cart_cookie_to_redis(request, response)

        # 响应
        return response
