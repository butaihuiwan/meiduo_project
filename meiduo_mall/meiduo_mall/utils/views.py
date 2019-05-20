# 创建Mixin扩展类
from django.contrib.auth.decorators import login_required


class LoginRequired(object):

    @classmethod
    def as_view(cls,**initkwargs):

        view = super().as_view()
        return login_required(view)
