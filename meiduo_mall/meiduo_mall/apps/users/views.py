from django.shortcuts import render, redirect
from django.views import View
from django import http
from django.contrib.auth import login, logout
import re
from .models import User, Address
from django_redis import get_redis_connection
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from meiduo_mall.utils.response_code import RETCODE
from celery_tasks.mail.tasks import send_user_email
from django.conf import settings
from meiduo_mall.utils import meiduo_signature
from . import contants
from carts.utils import merge_cart_cookie_to_redis


class RegisterView(View):
    def get(self, request):
        '''
        响应注册页面
        '''
        # 1.接收
        # 2.验证
        # 3.处理
        # 4.响应：展示注册页面
        return render(request, 'register.html')

    def post(self, request):
        '''
        创建用户对象，保存到表中
        '''
        # 1.接收
        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        phone = request.POST.get('phone')
        allow = request.POST.get('allow')
        sms_code_request = request.POST.get('msg_code')

        # 2.验证
        # 2.1非空
        if not all([user_name, pwd, cpwd, phone, allow, sms_code_request]):
            return http.HttpResponseBadRequest('参数不完整')
        # 2.2用户名格式
        if not re.match('^[a-zA-Z0-9_-]{5,20}$', user_name):
            return http.HttpResponseBadRequest('请输入5-20个字符的用户名')
        # 2.3用户名是否存在
        if User.objects.filter(username=user_name).count() > 0:
            return http.HttpResponseBadRequest('用户名已存在')
        # 2.4密码格式
        if not re.match('^[0-9A-Za-z]{8,20}$', pwd):
            return http.HttpResponseBadRequest('请输入8-20位的密码')
        # 2.5两个密码是否一致
        if pwd != cpwd:
            return http.HttpResponseBadRequest('两个密码不一致')
        # 2.6手机号格式
        if not re.match('^1[345789]\d{9}$', phone):
            return http.HttpResponseBadRequest('手机号格式错误')
        # 2.7手机号是否存在
        if User.objects.filter(mobile=phone).count() > 0:
            return http.HttpResponseBadRequest('手机号已存在')
        # 2.8allow对应的是复选框checkbox，如果不选中，则在请求报文中不包含这个数据，在非空已经验证，不需要再验证

        # 2.9验证短信验证码
        # 2.9.1连接redis，获取短信验证码
        redis_cli = get_redis_connection('verify_code')
        sms_code_redis = redis_cli.get('sms_' + phone)
        # 2.9.2判断过期
        if sms_code_redis is None:
            return http.HttpResponseBadRequest('短信验证码已过期')
        # 2.9.3是否一致
        if sms_code_redis.decode() != sms_code_request:
            return http.HttpResponseBadRequest('短信验证码错误')
        # 2.9.4强制过期
        redis_cli.delete('sms_' + phone)

        # 3.处理
        # 3.1保存用户对象
        # 问题：直接将数据保存到表中，而此处的密码需要加密再保存
        # user = User.objects.create(username=user_name, password=pwd, mobile=phone)
        # 解决：使用认证模块提供的创建用户的方法
        user = User.objects.create_user(username=user_name, password=pwd, mobile=phone)

        # 3.2状态保持
        # request.session['user_id']=user.id
        login(request, user)

        # 4.响应
        response = redirect('/')
        response.set_cookie('username', user.username, max_age=60 * 60 * 24 * 14)

        # 合并购物车
        response = merge_cart_cookie_to_redis(request, response)

        return response


class UsernameCheckView(View):
    def get(self, request, username):
        # 接收、验证：在路由规定中已经完成

        # 处理：查询用户名对应对象的个数
        count = User.objects.filter(username=username).count()

        # 响应：对应ajax请求，返回json数据
        return http.JsonResponse({
            'count': count
        })


class MobileCheckView(View):
    def get(self, request, mobile):
        # 处理
        count = User.objects.filter(mobile=mobile).count()

        # 响应
        return http.JsonResponse({
            'count': count
        })


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 接收
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        next_url = request.GET.get('next', '/')

        # 验证
        # 2.1非空
        if not all([username, pwd]):
            return http.HttpResponseBadRequest('参数不完整')
        # 2.2用户名格式
        if not re.match('^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseBadRequest('请输入5-20个字符的用户名')
        # 2.3密码格式
        if not re.match('^[0-9A-Za-z]{8,20}$', pwd):
            return http.HttpResponseBadRequest('请输入8-20位的密码')

        # 处理：查询，状态保持
        user = authenticate(username=username, password=pwd)
        if user is None:
            # 用户名或密码错误
            return render(request, 'login.html', {
                'loginerror': '用户名或密码错误'
            })
        else:
            # 用户名或密码正确，则状态保持，重定向
            login(request, user)

            # 输出cookie，用于前端提示
            response = redirect(next_url)
            response.set_cookie('username', user.username, max_age=60 * 60 * 24 * 14)

            # 合并购物车
            response = merge_cart_cookie_to_redis(request, response)

            return response

            # 响应


class LogoutView(View):
    def get(self, request):
        # 登出，本质删session
        logout(request)
        # 删除cookie中的提示
        response = redirect('/')
        response.delete_cookie('username')

        return response


class InfoView(LoginRequiredMixin, View):
    def get(self, request):
        # if not request.user.is_authenticated:
        #     return redirect('/login/')

        user = request.user
        context = {
            'username': user.username,
            'mobile': user.mobile,
            'email': user.email,
            'email_active': user.email_active
        }
        return render(request, 'user_center_info.html', context)


class EmailView(LoginRequiredMixin, View):
    def put(self, request):
        # 接收
        dict1 = json.loads(request.body.decode())
        email = dict1.get('email')

        # 验证
        if not all([email]):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '没有邮箱数据'
            })
        if not re.match('^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '邮箱格式错误'
            })

        # 处理
        user = request.user
        user.email = email
        user.save()

        # 调用发邮件的任务
        token = meiduo_signature.dumps({'user_id': user.id}, contants.EMAIL_ACTIVE_EXPIRES)
        url = settings.EMAIL_ACTIVE_URL + '?token=%s' % token
        send_user_email.delay(email, url)

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok'
        })


class EmailActiveView(View):
    def get(self, request):
        # 接收
        token = request.GET.get('token')

        # 验证
        if not all([token]):
            return http.HttpResponseBadRequest('参数不完整')
        json = meiduo_signature.loads(token, contants.EMAIL_ACTIVE_EXPIRES)
        if json is None:
            return http.HttpResponseBadRequest('激活链接无效')
        user_id = json.get('user_id')
        # 处理
        try:
            user = User.objects.get(pk=user_id)
        except:
            return http.HttpResponseBadRequest('激活链接无效')
        else:
            user.email_active = True
            user.save()
        # 响应
        return redirect('/info/')


class AddressView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        # 查询当前用户的收货地址
        address_list = Address.objects.filter(user=user, is_delete=False)
        # 遍历，将address对象转换成字典
        addresses = []
        for address in address_list:
            addresses.append(address.to_dict())

        context = {
            'addresses': addresses,
            'default_address_id': user.default_address_id
        }
        return render(request, 'user_center_site.html', context)


class AddressCreateView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        # 接收post，ajax
        # request.POST====><form method='post'></form>
        # request.GET======>查询参数
        # request.body=====>接收ajax中的json数据
        dict1 = json.loads(request.body.decode())
        receiver = dict1.get('receiver')
        province_id = dict1.get('province_id')
        city_id = dict1.get('city_id')
        district_id = dict1.get('district_id')
        detail = dict1.get('place')
        mobile = dict1.get('mobile')
        tel = dict1.get('tel')
        email = dict1.get('email')

        # 验证
        if not all([receiver, province_id, city_id, district_id, detail, mobile]):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '参数不完整'
            })
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '手机号格式错误'
            })
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.JsonResponse({
                    'code': RETCODE.PARAMERR,
                    'errmsg': '固定电话格式错误'
                })
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.JsonResponse({
                    'code': RETCODE.PARAMERR,
                    'errmsg': '邮箱格式错误'
                })

        # 处理：创建收货地址对象
        address = Address.objects.create(
            user=user,
            title=receiver,
            receiver=receiver,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            detail=detail,
            mobile=mobile,
            tel=tel,
            email=email
        )

        # 如果当前用户没有默认收货地址，则设置默认
        if user.default_address is None:
            user.default_address = address
            # user.default_address_id = address.id
            user.save()

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'address': address.to_dict()
        })


class AddressUpdateView(LoginRequiredMixin, View):
    def put(self, request, address_id):
        user = request.user
        # 接收
        dict1 = json.loads(request.body.decode())
        receiver = dict1.get('receiver')
        province_id = dict1.get('province_id')
        city_id = dict1.get('city_id')
        district_id = dict1.get('district_id')
        detail = dict1.get('place')
        mobile = dict1.get('mobile')
        tel = dict1.get('tel')
        email = dict1.get('email')

        # 验证
        if not all([receiver, province_id, city_id, district_id, detail, mobile]):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '参数不完整'
            })
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '手机号格式错误'
            })
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.JsonResponse({
                    'code': RETCODE.PARAMERR,
                    'errmsg': '固定电话格式错误'
                })
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.JsonResponse({
                    'code': RETCODE.PARAMERR,
                    'errmsg': '邮箱格式错误'
                })
        # 处理
        # 1.查询
        try:
            address = Address.objects.get(pk=address_id, user=user, is_delete=False)
        except:
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': "收货地址编号无效"
            })
        # 2.赋新值
        address.receiver = receiver
        address.province_id = province_id
        address.city_id = city_id
        address.district_id = district_id
        address.detail = detail
        address.mobile = mobile
        address.tel = tel
        address.email = email
        # 3.保存
        address.save()

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok',
            'address': address.to_dict()
        })

    def delete(self, request, address_id):
        # 逻辑删除，本质就是修改
        try:
            address = Address.objects.get(pk=address_id, user=request.user, is_delete=False)
        except:
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '编号无效'
            })
        address.is_delete = True
        address.save()
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok'
        })


class AddressDefaultView(LoginRequiredMixin, View):
    def put(self, request, address_id):
        user = request.user
        user.default_address_id = address_id
        # user.default_address
        user.save()
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok'
        })


class AddressTitleView(LoginRequiredMixin, View):
    def put(self, request, address_id):
        # 接收
        dict1 = json.loads(request.body.decode())
        title = dict1.get('title')

        if not all([title]):
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '缺少标题'
            })

        # 查询
        try:
            address = Address.objects.get(pk=address_id, user=request.user, is_delete=False)
        except:
            return http.JsonResponse({
                'code': RETCODE.PARAMERR,
                'errmsg': '收货地址编号无效'
            })

        address.title = title
        address.save()

        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': 'ok'
        })


class PasswordView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'user_center_pass.html')

    def post(self, request):
        # 接收
        old_pwd = request.POST.get('old_pwd')
        new_pwd = request.POST.get('new_pwd')
        new_cpwd = request.POST.get('new_cpwd')
        user = request.user

        # 验证
        if not all([old_pwd, new_pwd, new_cpwd]):
            return http.HttpResponseBadRequest('数据不能为空')
        # 格式
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', new_pwd):
            return http.HttpResponseBadRequest('新密码格式错误')
        if new_pwd != new_cpwd:
            return http.HttpResponseBadRequest('两个新密码不一致')
        if not user.check_password(old_pwd):
            return http.HttpResponseBadRequest('原始密码错误')

        # 处理
        user.set_password(new_pwd)
        user.save()

        # 响应
        return render(request, 'user_center_pass.html')
