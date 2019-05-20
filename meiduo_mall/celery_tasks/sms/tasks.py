from celery_tasks.main import celery_app
from celery_tasks.yuntongxun.ccp_sms import CCP


@celery_app.task(bind=True,name='ccp_send_sms_code')
def send_sms_code(self,mobile,sms_code):
    try:
        result = CCP().send_template_sms(mobile, [sms_code,5],1)

    except Exception as e :
        pass

    return result

