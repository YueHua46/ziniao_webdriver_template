import os
from dotenv import load_dotenv

load_dotenv()


def _strip_env(value, default=None):
    """去除 .env 值的首尾空白、引号和行内注释（# 及其后内容），避免被误解析"""
    if value is None:
        return default if default is not None else ""
    s = str(value).strip()
    if " #" in s:
        s = s.split(" #", 1)[0].strip()
    s = s.strip('"').strip("'")
    return s


def _strip_path(value):
    """路径专用：与 _strip_env 一致，默认返回空字符串"""
    return _strip_env(value, "")


# 紫鸟浏览器配置
ZINIAO_CONFIG = {
    'client_path': _strip_path(os.getenv('ZINIAO_CLIENT_PATH')),
    'driver_folder_path': _strip_path(os.getenv('ZINIAO_DRIVER_FOLDER_PATH')),
    'socket_port': _strip_env(os.getenv('ZINIAO_SOCKET_PORT'), "16851"),
    'user_info': {
        'company': _strip_env(os.getenv('ZINIAO_COMPANY')),
        'username': _strip_env(os.getenv('ZINIAO_USERNAME')),
        'password': _strip_env(os.getenv('ZINIAO_PASSWORD')),
    },
    'debuggingPort': _strip_env(os.getenv('ZINIAO_DEBUGGING_PORT'), "9222"),
}