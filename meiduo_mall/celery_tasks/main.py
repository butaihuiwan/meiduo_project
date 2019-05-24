# celery 启动文件
from celery import Celery


# 为 celery 使用 django 配置文件进行设置

import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'


# 创建celery对象

celery_app = Celery('meiduo')

# 给celery添加配置

celery_app.config_from_object('celery_tasks.config')


# 寻找任务
celery_app.autodiscover_tasks(['celery_tasks.sms','celery_tasks.email'])