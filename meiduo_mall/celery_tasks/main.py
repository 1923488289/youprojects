from celery import Celery
import os

# 加载django配置
os.environ["DJANGO_SETTINGS_MODULE"] = "meiduo_mall.settings.dev"

# 创建celery对象
celery_app = Celery()
# 加载配置，指定了消息队列使用redis
celery_app.config_from_object('celery_tasks.config')

# 自动识别任务
celery_app.autodiscover_tasks([
    'celery_tasks.sms',
    'celery_tasks.mail',
    'celery_tasks.detail',
])
