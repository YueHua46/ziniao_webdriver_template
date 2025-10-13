import os
from dotenv import load_dotenv

load_dotenv()

# 紫鸟浏览器配置
ZINIAO_CONFIG = {
    'client_path': f"{os.getenv('ZINIAO_CLIENT_PATH')}", # 紫鸟客户端路径
    'driver_folder_path': f"{os.getenv('ZINIAO_DRIVER_FOLDER_PATH')}", # 存放紫鸟驱动文件的文件夹路径
    'socket_port': f"{os.getenv('ZINIAO_SOCKET_PORT', 16851)}", # 紫鸟Socket端口
    'user_info': {
        'company': f"{os.getenv('ZINIAO_COMPANY')}", # 紫鸟公司名称
        'username': f"{os.getenv('ZINIAO_USERNAME')}", # 紫鸟用户名
        'password': f"{os.getenv('ZINIAO_PASSWORD')}" # 紫鸟密码
    },
    'debuggingPort': f"{os.getenv('ZINIAO_DEBUGGING_PORT', 9222)}" # 紫鸟调试端口
}