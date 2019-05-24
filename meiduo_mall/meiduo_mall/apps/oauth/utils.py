from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer, BadData


def generate_access_token(openid):

    # TimedJSONWebSignatureSerializer(秘钥, 有效期秒)
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 300)

    data = {'openid':openid}
    # serializer.dumps(数据), 返回 bytes 类型
    token = serializer.dumps(data)
    return token.decode()



def check_access_token(access_token):
    """

    :param access_token:
    :return:
    """
    # TimedJSONWebSignatureSerializer(秘钥, 有效期秒)
    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 300)
    try:
        data = serializer.loads(access_token)

    except BadData:
        return None

    else:
        return data.get('openid')