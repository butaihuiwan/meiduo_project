import json
import re

from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django.urls import reverse
from django_redis import get_redis_connection

from django.contrib.auth import login, authenticate, logout
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django import http

# Create your views here.
# from django.urls import reverse
from django.views import View

from meiduo_mall.utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequired
from oauth.models import OAuthQQUser
from oauth.utils import generate_access_token, check_access_token

from user.models import User
import logging

logger = logging.getLogger('django')


# 添加验证邮箱接口
class VerifyEmailView(View):
    """验证邮箱"""

    def get(self, request):
        """实现邮箱验证逻辑"""
        # 接收参数
        token = request.GET.get('token')

        # 校验参数：判断 token 是否为空和过期，提取 user
        if not token:
            return http.HttpResponseBadRequest('缺少token')

        # 调用上面封装好的方法, 将 token 传入
        user = User.check_verify_email_token(token)
        if not user:
            return http.HttpResponseForbidden('无效的token')

        # 修改 email_active 的值为 True
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮件失败')

        # 返回邮箱验证结果
        return redirect(reverse('user:info'))


# 添加邮箱接口

class EmailView(View):
    """添加邮箱"""

    def put(self, request):
        """实现接受邮箱逻辑"""

        # # 判断是否位登陆用户 方法一：
        # if not request.user.is_authenticated():
        #     return http.JsonResponse({'code': RETCODE.SESSIONERR, 'errmsg': '用户未登录'})

        # 1. 接受参数
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        # 校验参数
        if not email:
            return http.HttpResponseForbidden('缺少必要参数')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('邮箱格式错误')

        # 保存邮箱数据
        try:
            request.user.email = email
            request.user.save()

        except Exception as e:
            logger.error(e)

            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})

        from celery_tasks.email.tasks import send_verify_email

        # 用定义好的函数替换原来的字符串:
        verify_url = request.user.generate_verify_email_url()
        # 异步发送邮件
        send_verify_email.delay(email, verify_url)

        # 返回添加邮箱响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮箱成功'})


# qq用户绑定处理
class QQUserView(View):

    def get(self, request):
        # 提取code请求参数

        code = request.GET.get('code')
        if not code:
            return http.HttpResponseForbidden('缺少参数')
        # 创建工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)
        try:
            access_token = oauth.get_access_token(code)
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('OAuth2.0认证失败')

        try:
            oauth_user = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            access_token = generate_access_token(openid)
            context = {
                'access_token': access_token
            }
            return render(request, 'oauth_callback.html', context)


        else:
            qq_user = oauth_user.user
            login(request, qq_user)
        response = redirect(reverse('contents:index'))
        response.set_cookie('username', qq_user.username, max_age=3600 * 24 * 15)

        return response

    def post(self, request):
        """美多商城用户绑定到openid"""

        # 1.接收参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code_client = request.POST.get('sms_code')
        access_token = request.POST.get('access_token')

        # 2.校验参数
        if not all([mobile, password, sms_code_client]):
            return http.HttpResponseForbidden('缺少必要参数')

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')

        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        # 创建redis连接，判断短信验证码是否一致

        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '无效的短信验证码'})

        if sms_code_server.decode() != sms_code_client:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入短信验证码有误'})

        openid = check_access_token(access_token)
        if not openid:
            return render(request, 'oauth_callback.html', {'openid_errmsg': '无效的openid'})

        # 4.保存注册信息
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:

            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        else:
            if not user.check_password(password):
                return render(request, 'oauth_callback.html', {'account_errmsg': '用户名或密码错误'})

        try:
            OAuthQQUser.objects.create(openid=openid, user=user)
        except DatabaseError:
            return render(request, 'oauth_callback.html', {'qq_login_errmsg': 'QQ登录失败'})
        # 状态保持
        login(request, user)

        # 返回
        next = request.GET.get('next', '/')
        response = redirect(next)
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)
        return response


# QQ登陆网址接口
class QQURLView(View):

    def get(self, request):
        next = request.GET.get('next')

        # 创建OAuthQQ对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                        client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI,
                        state=next)

        # 调用对象的获取qq的地址方法

        login_url = oauth.get_qq_url()

        # 返回登陆地址

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok', 'login_url': login_url})


# 用户中心显示接口
class UserInfoView(LoginRequired, View):
    """用户中心"""

    def get(self, request):
        """提供个人信息界面"""
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }

        return render(request, 'user_center_info.html', context)


# 退出登陆接口
class LogoutView(View):

    def get(self, request):
        logout(request)

        response = redirect(reverse('contents:index'))

        response.delete_cookie('username')
        return response


# 登陆接口

class LoginView(View):
    """用户名登陆"""

    def get(self, request):
        """提供登陆界面的接口"""
        return render(request, 'login.html')

    def post(self, request):
        # 实现登陆逻辑
        # 1. 获取前端传递参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 2. 校验参数
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必要参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8为，最多20位字符')

        # 3. 获取登录用户,并查看是否存在
        user = authenticate(username=username, password=password)
        if user is None:
            return http.HttpResponseForbidden('用户名或密码错误')

        # 4. 实现状态保持
        login(request, user)

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

    def get(self, request):
        pass

        return render(request, 'register.html')

    def post(self, request):

        # 接受请求数据参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')
        # TODO 短信验证码

        # 判断参数是否齐全

        if not all([username, password, password2, mobile, allow, sms_code_client]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 判断用户名是否是5-20个字符

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')

        # 判断两次密码是否一致

        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号')

        # 判断短信验证码是否正确

        if sms_code_client is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '验证码失效'})

        redis_conn = get_redis_connection('verify_code')

        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_client != sms_code_server.decode():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入的短信验证码错误'})

        # 判断是否勾选用户协议

        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # 保存注册的数据
        try:
            user = User.objects.create_user(username=username, password=password,
                                            mobile=mobile)

        except DatabaseError:
            return render(request, 'register,html', {'register_errmsg': '注册失败'})

        # 状态保持
        login(request, user)
        # return http.HttpResponse('注册成功，重定向到首页')
        response = render(request, 'index.html')

        # 在响应对象中设置用户名信息.
        # 将用户名写入到 cookie，有效期 15 天
        response.set_cookie('username', user.username)

        # 返回响应结果
        return response


# 用户名重复注册后端逻辑

class UsernameCountView(View):
    """判断用户是否重复注册"""

    def get(self, request, username):
        """

        :param request: 请求对象

        :return:Json
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok', 'count': count})


# 手机号重复注册后端逻辑

class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self, request, mobile):
        """

        :param request: 请求对象
        :param mobile:  手机号
        :return: JSON
        """

        count = User.objects.filter(mobile=mobile).count()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'ok', 'count': count})
