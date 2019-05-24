import random

from django import http
from django.views import View

from meiduo_mall.apps.verifications import constants
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import get_redis_connection

from meiduo_mall.libs.yuntongxun.ccp_sms import CCP
from meiduo_mall.utils.response_code import RETCODE
import logging

logger = logging.getLogger('django')


class ImageCodeView(View):
    """
    图形验证码
    """
    def get(self,request,uuid):
        """

        :param request:
        :param uuid:
        :return: image/jpg
        """
        text, image = captcha.generate_captcha()

        redis_conn = get_redis_connection('verify_code')

        redis_conn.setex('img_%s' % uuid, constants.IMAGE_CODE_REDIS_EXPIRES,text)

        return http.HttpResponse(image,content_type='image/jpg')





# 短信验证码

class SMSCodeView(View):
    """短信验证码"""
    def get(self,request,mobile):
        # 3.创建连接到redis的对象
        redis_conn = get_redis_connection('verify_code')
        get = redis_conn.get('sms_flag_%s' % mobile)
        if get:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'发送短信过于频繁'})
        """

        :param request: 请求对象
        :param mobile:  手机号
        :return: JSON
        """
        # 1.接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('image_code_id')

        # 2.校验参数
        if not all([image_code_client,uuid]):
            return http.JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'缺少必要参数'})





        # 4.提取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        # 判断图形验证码是否存在
        if image_code_server is None:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图形验证码失效'})

        # 删除图形验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logging.error(e)

        # 对比图形验证码
        image_code_server=image_code_server.decode()
        if image_code_server.lower() != image_code_client.lower():
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'输入验证码错误'})

        # 生成短信验证码，生成6位数验证码
        sms_code = '%06d' % random.randint(0,999999)
        logger.info(sms_code)

        # 创建管道
        pl = redis_conn.pipeline()

        # 保存短信验证码
        pl.setex('sms_%s' % mobile, constants.IMAGE_CODE_REDIS_EXPIRES,sms_code)
        pl.setex('sms_flag_%s' % mobile, constants.IMAGE_CODE_REDIS_EXPIRES,sms_code)

        pl.execute()


        #发送短信验证码
        CCP().send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIS_EXPIRES],1)
        from celery_tasks.sms.tasks import send_sms_code
        send_sms_code.delay(mobile,sms_code)



        # 响应结果
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'短信发送成功'})

