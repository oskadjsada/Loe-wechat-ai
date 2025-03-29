import time
import uuid
import json
import threading
from common.log import logger

def generate_request_id():
    """
    生成唯一请求ID
    :return: 唯一ID
    """
    return f"{int(time.time() * 1000)}-{str(uuid.uuid4())[:8]}"

def async_run(func, *args, **kwargs):
    """
    异步执行函数
    :param func: 要执行的函数
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 线程对象
    """
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

# 简单的消息ID管理
class MessageIdManager:
    """
    简单的消息ID管理器，用于检查消息是否处理过
    """
    def __init__(self, max_size=1000):
        self.message_ids = set()
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def add_message_id(self, message_id):
        """
        添加消息ID
        :param message_id: 消息ID
        :return: 如果是新消息ID返回True，否则返回False
        """
        with self.lock:
            if message_id in self.message_ids:
                return False
                
            self.message_ids.add(message_id)
            
            # 如果超出最大容量，清理一半
            if len(self.message_ids) > self.max_size:
                self.message_ids = set(list(self.message_ids)[-(self.max_size // 2):])
                
            return True
    
    def has_message_id(self, message_id):
        """
        检查消息ID是否存在
        :param message_id: 消息ID
        :return: 存在返回True，否则返回False
        """
        with self.lock:
            return message_id in self.message_ids

# 全局消息ID管理器
message_id_manager = MessageIdManager()