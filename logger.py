import logging
from logging.handlers import TimedRotatingFileHandler
import os

# 确保日志目录存在
log_dir = './logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 创建logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建按日期轮转的文件处理器
# when='midnight': 每天午夜创建新的日志文件
# interval=1: 每1天轮转一次
# backupCount=30: 保留最近30天的日志文件，超过30天的自动删除
# encoding='utf-8': 支持中文日志
fh = TimedRotatingFileHandler(
    filename='./logs/running.log',
    when='midnight',           # 每天午夜轮转
    interval=1,                # 轮转间隔：1天
    backupCount=30,            # 保留30天的日志
    encoding='utf-8',          # 支持中文
    delay=False,
    utc=False                  # 使用本地时间
)
fh.setLevel(logging.DEBUG)
# 设置日志文件的日期后缀格式为：YYYY-MM-DD
fh.suffix = "%Y-%m-%d"

# 创建控制台处理器
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# 创建格式化器
formatter = logging.Formatter('[%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s] - %(message)s')

# 设置格式化器
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(fh)
logger.addHandler(ch)