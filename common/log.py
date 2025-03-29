import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import sys
import time

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

# 默认日志级别
DEFAULT_LOG_LEVEL = logging.INFO

# 创建过滤器类，过滤掉图标相关的警告
class IconFilter(logging.Filter):
    def filter(self, record):
        # 如果消息包含以下关键词，且级别为WARNING或更低，则不显示
        if record.levelno <= logging.WARNING and any(keyword in record.getMessage() for keyword in 
                                                  ['图标', 'icon', '托盘']):
            return False
        return True

class WechatFilter(logging.Filter):
    """过滤器，针对微信消息进行特殊处理"""
    
    def __init__(self, name=''):
        super().__init__(name)
        self.last_verify_time = 0
        self.verify_count = 0
    
    def filter(self, record):
        msg = record.getMessage()
        
        # 合并连续的验证成功日志
        if "微信公众号接入验证成功" in msg:
            current_time = time.time()
            # 如果最近5秒内有验证成功日志，则计数并不记录
            if current_time - self.last_verify_time < 5:
                self.verify_count += 1
                # 每10次验证成功才记录一次，避免日志过多
                if self.verify_count % 10 != 0:
                    return False
            else:
                # 重置计数器
                self.verify_count = 1
            
            self.last_verify_time = current_time
        
        return True

# 创建logger
logger = logging.getLogger('wechat-deepseek')
logger.setLevel(DEFAULT_LOG_LEVEL)

# 添加控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(DEFAULT_LOG_LEVEL)
console_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
console_handler.setFormatter(console_formatter)
# 添加图标过滤器
console_handler.addFilter(IconFilter())
# 添加微信消息过滤器
console_handler.addFilter(WechatFilter())
logger.addHandler(console_handler)

def init_logger(log_dir=None, log_level=None):
    """
    初始化日志配置
    :param log_dir: 日志保存目录
    :param log_level: 日志级别
    """
    global logger

    # 设置日志级别
    if log_level:
        try:
            level = getattr(logging, log_level.upper())
            logger.setLevel(level)
            console_handler.setLevel(level)
            logger.info(f"设置日志级别为: {log_level.upper()}")
        except AttributeError:
            logger.warning(f"无效的日志级别: {log_level}，使用默认级别: INFO")
            logger.setLevel(DEFAULT_LOG_LEVEL)
            console_handler.setLevel(DEFAULT_LOG_LEVEL)

    # 设置文件处理器
    if log_dir:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 主日志文件 - 按大小轮转
        log_file = os.path.join(log_dir, 'wechat-deepseek.log')
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logger.level)
        file_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        # 添加微信消息过滤器
        file_handler.addFilter(WechatFilter())
        logger.addHandler(file_handler)
        
        # 每日轮转的调试日志
        if logger.level <= logging.DEBUG:
            debug_log_file = os.path.join(log_dir, 'debug.log')
            debug_file_handler = TimedRotatingFileHandler(
                debug_log_file,
                when='midnight',
                interval=1,  # 每天一个新文件
                backupCount=7  # 保留7天的日志
            )
            debug_file_handler.setLevel(logging.DEBUG)
            debug_file_handler.setFormatter(file_formatter)
            logger.addHandler(debug_file_handler)
        
        # 错误日志单独保存
        error_log_file = os.path.join(log_dir, 'error.log')
        error_file_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(file_formatter)
        logger.addHandler(error_file_handler)
        
        # 微信请求专用日志
        wechat_log_file = os.path.join(log_dir, 'wechat_requests.log')
        wechat_file_handler = RotatingFileHandler(
            wechat_log_file,
            maxBytes=20*1024*1024,  # 20MB
            backupCount=3
        )
        wechat_file_handler.setLevel(logging.INFO)
        wechat_file_handler.setFormatter(file_formatter)
        
        # 添加过滤器，只记录微信请求相关日志
        class WechatRequestFilter(logging.Filter):
            def filter(self, record):
                msg = record.getMessage()
                return any(keyword in msg for keyword in 
                          ['微信GET请求', '微信POST请求', '微信POST数据', '收到微信消息'])
        
        wechat_file_handler.addFilter(WechatRequestFilter())
        logger.addHandler(wechat_file_handler)
    
    logger.info(f"日志初始化完成，级别: {logging.getLevelName(logger.level)}, 目录: {log_dir or '无'}")
    return logger 