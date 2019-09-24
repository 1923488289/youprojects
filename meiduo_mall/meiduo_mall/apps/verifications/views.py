from django.shortcuts import render
from django.views import View
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from . import constants
from django import http
from meiduo_mall.utils.response_code import RETCODE
import random
from meiduo_mall.libs.yuntongxun.sms import CCP
from celery_tasks.sms.tasks import send_sms
import time

class ImagecodeView(View):
    def get(self, request, uuid):
        # 接收,验证
        # 处理
        # 1.生成字符code、图片image
        text, code, image = captcha.generate_captcha()

        # 2.保存字符
        # 2.1连接redis，参数是caches中的键
        redis_cli = get_redis_connection('verify_code')
        # 2.2保存
        redis_cli.setex(uuid, constants.IMAGE_CODE_EXPIRES, code)

        # 响应：图片
        return http.HttpResponse(image, content_type='image/png')


class SmscodeView(View):
    def get(self, request, mobile):
        # 接收
        image_code_request = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 验证
        # 1.图片验证码是否正确
        # 1.1读取redis中的图片验证码
        redis_cli = get_redis_connection('verify_code')
        image_code_redis = redis_cli.get(uuid)
        # 1.2判断是否过期
        if image_code_redis is None:
            return http.JsonResponse({
                'code': RETCODE.IMAGECODEERR,
                'errmsg': '图片验证码已经过期'
            })
        # 1.3对比
        # 注意1：在redis读取的数据，都是bytes类型
        # 注意2：不区分大小写
        if image_code_redis.decode() != image_code_request.upper():
            return http.JsonResponse({
                'code': RETCODE.IMAGECODEERR,
                'errmsg': '图片验证码错误'
            })
        # 1.4强制图片验证码过期
        redis_cli.delete(uuid)

        # 2.在60秒内只向指定手机号发一次短信
        if redis_cli.get('sms_flag_' + mobile):
            return http.JsonResponse({
                'code': RETCODE.SMSCODERR,
                'errmsg': '发送短信太频繁'
            })

        # 处理
        # 1.生成6位随机数
        sms_code = '%06d' % random.randint(0, 999999)

        # # 2.保存到redis中
        # redis_cli.setex('sms_' + mobile, constants.SMS_CODE_EXPIRES, sms_code)
        # # 是否在60秒内发送短信的标记
        # redis_cli.setex('sms_flag_' + mobile, constants.SMS_CODE_FLAG_EXPIRES, 1)

        # 优化redis：只与redis服务器交互一次
        redis_pl = redis_cli.pipeline()
        redis_pl.setex('sms_' + mobile, constants.SMS_CODE_EXPIRES, sms_code)
        redis_pl.setex('sms_flag_' + mobile, constants.SMS_CODE_FLAG_EXPIRES, 1)
        redis_pl.execute()

        # 3.发短信
        # time.sleep(5)
        # ccp = CCP()
        # ccp.send_template_sms(mobile, [sms_code, constants.SMS_CODE_EXPIRES / 60], 1)
        # print(sms_code)
        # 调用任务
        send_sms.delay(mobile, [sms_code, constants.SMS_CODE_EXPIRES / 60], 1)

        # 响应
        return http.JsonResponse({
            'code': RETCODE.OK,
            'errmsg': "OK"
        })
