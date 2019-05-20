from celery import Celery

# 创建celery对象

celery_app = Celery('meiduo')

# 给celery添加配置

celery_app.config_from_object('celery_tasks.config')


# 寻找任务
celery_app.autodiscover_tasks(['celery_tasks.sms'])