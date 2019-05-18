import re

from django.contrib.auth import login
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django import http

# Create your views here.
from django.urls import reverse
from django.views import View

from meiduo_mall.utils.response_code import RETCODE
from user.models import User


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
        allow = request.POSTget('allow')
        # TODO 短信验证码

        # 判断参数是否齐全

        if not all([username,password,password2,mobile,allow]):
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
        return redirect(reverse('contents:index'))



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











