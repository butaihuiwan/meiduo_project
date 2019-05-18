from django import http
from django.views import View

from meiduo_mall.apps.verifications import constants
from meiduo_mall.libs.captcha.captcha import captcha
from django_redis import  get_redis_connection


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



