from abc import ABC, abstractmethod

class Channel(ABC):
    """
    通道抽象基类，所有的通道类都要继承此类
    """
    
    @abstractmethod
    def startup(self):
        """
        启动通道
        """
        pass
    
    @abstractmethod
    def handle_message(self, message):
        """
        处理消息
        :param message: 消息内容
        :return: 处理结果
        """
        pass 