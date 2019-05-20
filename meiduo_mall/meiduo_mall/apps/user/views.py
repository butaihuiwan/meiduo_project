import re

from django.urls import reverse
from django_redis import  get_redis_connection

from django.contrib.auth import login, authenticate, logout
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django import http

# Create your views here.
# from django.urls import reverse
from django.views import View

from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequired

from user.models import User




# 用户中心显示接口
class UserInfoView(LoginRequired,View):
    """用户中心"""
    def get(self,request):
        return render(request,'user_center_info.html')


# 退出登陆接口
class LogoutView(View):

    def get(self,request):
        logout(request)


        response = redirect(reverse('contents:index'))

        response.delete_cookie('username')
        return response

# 登陆接口

class LoginView(View):
    """用户名登陆"""

    def get(self,request):
        """提供登陆界面的接口"""
        return render(request,'login.html')

    def post(self,request):
        # 实现登陆逻辑
        # 1. 获取前端传递参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')


        # 2. 校验参数
        if not all([username,password]):
            return http.HttpResponseForbidden('缺少必要参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden('请输入正确的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8为，最多20位字符')


        # 3. 获取登录用户,并查看是否存在
        user = authenticate(username=username, password=password)
        if user is None:
            return http.HttpResponseForbidden('用户名或密码错误')

        # 4. 实现状态保持
        login(request,user)

        if remembered != 'on':
            request.session.set_expiry(0)
        else:

            request.session.set_expiry(None)

        # response = render(request,'index.html')
        response = redirect(reverse('contents:index'))


        # 在响应对象中设置用户名信息.
        # 将用户名写入到 cookie，有效期 15 天
        response.set_cookie('username', user.username)

        # 返回响应结果
        return response
        # return render(request,'index.html')









# 注册接口

class Register(View):

    def get(self,request):
        pass

        return render(request, 'register.html')

    def post(self,request):

        # 接受请求数据参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')
        # TODO 短信验证码

        # 判断参数是否齐全

        if not all([username,password,password2,mobile,allow,sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 判断用户名是否是5-20个字符

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')

        # 判断两次密码是否一致

        if password != password2:
             return http.HttpResponseForbidden('两次输入的密码不一致')

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$',mobile):
             return http.HttpResponseForbidden('请输入正确的手机号')

        # 判断短信验证码是否正确

        if sms_code_client is None:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'验证码失效'})

        redis_conn = get_redis_connection('verify_code')

        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_client != sms_code_server.decode():
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'输入的短信验证码错误'})

        # 判断是否勾选用户协议

        if allow != 'on':
             return http.HttpResponseForbidden('请勾选用户协议')



         # 保存注册的数据
        try:
            user = User.objects.create_user(username=username,password=password,
                                            mobile=mobile)

        except DatabaseError:
            return render(request,'register,html',{'register_errmsg': '注册失败'})

        # 状态保持
        login(request,user)
        # return http.HttpResponse('注册成功，重定向到首页')
        response = render(request,'index.html')


        # 在响应对象中设置用户名信息.
        # 将用户名写入到 cookie，有效期 15 天
        response.set_cookie('username', user.username)

        # 返回响应结果
        return response


# 用户名重复注册后端逻辑

class UsernameCountView(View):
    """判断用户是否重复注册"""

    def get(self,request,username):
        """

        :param request: 请求对象

        :return:Json
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','count':count})



# 手机号重复注册后端逻辑

class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self,request,mobile):
        """

        :param request: 请求对象
        :param mobile:  手机号
        :return: JSON
        """

        count = User.objects.filter(mobile=mobile).count()

        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'ok','count':count})











