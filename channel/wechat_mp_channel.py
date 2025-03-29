#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import threading
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from common.log import logger
from common.utils import generate_request_id, async_run
from config import get_value

class WechatMpRequestHandler(BaseHTTPRequestHandler):
    """
    微信公众号请求处理器
    """
    def log_message(self, format, *args):
        """重写日志方法，不输出常规HTTP请求日志"""
        # 完全禁止HTTP请求日志输出
        pass
        
    def log_error(self, format, *args):
        """重写错误日志方法，不输出HTTP错误日志"""
        # 完全禁止HTTP错误日志输出
        pass
    
    def handle_one_request(self):
        """重写处理单个请求的方法，增加异常处理"""
        try:
            # 调用父类的处理方法
            super().handle_one_request()
        except ConnectionResetError:
            # 客户端重置连接，不记录错误，静默处理
            pass
        except ConnectionAbortedError:
            # 客户端中止连接，不记录错误，静默处理
            pass
        except BrokenPipeError:
            # 管道破裂，通常是客户端关闭连接，静默处理
            pass
        except socket.timeout:
            # 连接超时，静默处理
            pass
        except Exception as e:
            # 其他未知异常，记录日志但不中断服务
            logger.error(f"处理HTTP请求时发生异常: {str(e)}")
    
    def handle(self):
        """重写处理方法，增加异常处理"""
        try:
            # 调用父类的处理方法
            super().handle()
        except ConnectionResetError:
            pass
        except ConnectionAbortedError:
            pass
        except BrokenPipeError:
            pass
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"处理HTTP连接时发生异常: {str(e)}")
    
    def do_GET(self):
        """处理GET请求（公众号验证）"""
        try:
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            # 获取参数
            signature = params.get("signature", [""])[0]
            timestamp = params.get("timestamp", [""])[0]
            nonce = params.get("nonce", [""])[0]
            echostr = params.get("echostr", [""])[0]
            
            # 不再记录验证请求日志
            
            # 直接返回echostr，验证成功
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(echostr.encode("utf-8"))
            
            # 不记录验证成功日志
        
        except Exception as e:
            # 只记录严重错误
            logger.error(f"处理微信验证请求异常: {str(e)}")
            self.send_error(500, "Internal Server Error")
    
    def do_POST(self):
        """处理POST请求（接收微信消息）"""
        try:
            # 获取请求数据
            content_length = int(self.headers['Content-Length'])
            request_data = self.rfile.read(content_length)
            
            # 不再记录完整的XML请求内容
            # logger.debug(f"收到POST请求:\n{request_data.decode('utf-8')}")
            
            # 解析XML数据
            xml_data = request_data.decode('utf-8')
            
            # 从XML中提取必要信息
            from_user_match = re.search(r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>', xml_data)
            to_user_match = re.search(r'<ToUserName><!\[CDATA\[(.*?)\]\]></ToUserName>', xml_data)
            msg_type_match = re.search(r'<MsgType><!\[CDATA\[(.*?)\]\]></MsgType>', xml_data)
            
            if not (from_user_match and to_user_match and msg_type_match):
                logger.error("无法解析XML消息")
                self.send_error(400, "无法解析消息")
                return
            
            from_user = from_user_match.group(1)
            to_user = to_user_match.group(1)
            msg_type = msg_type_match.group(1)
            
            # 解析更多字段
            message = self.server.channel._parse_xml_to_dict(xml_data)
            
            # 记录消息内容 - 只在这里记录一次
            if msg_type == 'text':
                # 文本消息只记录内容
                content = message.get('Content', '')
                logger.info(f"[用户请求] {content}")
            elif msg_type == 'event':
                event = message.get('Event', '').lower()
                if event == 'subscribe':
                    logger.info("收到用户关注事件")
                else:
                    logger.info(f"收到事件: {event}")
            elif msg_type == 'voice':
                recognition = message.get("Recognition", "")
                if recognition:
                    logger.info(f"[语音识别] {recognition}")
            else:
                logger.info(f"收到消息类型: {msg_type}")
            
            # 根据消息类型处理
            response = None
            
            # 事件消息
            if msg_type == 'event':
                event = message.get('Event', '').lower()
                
                if event == 'subscribe':
                    # 处理关注事件
                    logger.info(f"用户关注事件: {from_user}")
                    response = self.server.channel.handle_subscribe_event(from_user, to_user)
                else:
                    logger.info(f"其他事件: {event}")
                    # 不处理的事件，返回空消息
                    response = self.server.channel.reply_empty(message)
            # 文本消息
            elif msg_type == 'text':
                content = message.get('Content', '')
                # 不再重复记录消息内容
                response = self.server.channel.handle_text_message(message)
            # 语音消息
            elif msg_type == 'voice':
                recognition = message.get("Recognition", "")
                if recognition:
                    logger.info(f"[语音识别] {recognition}")
                    response = self.server.channel.handle_text_message(message)
                else:
                    response = self.server.channel.reply_text(message, "抱歉，我无法识别您的语音")
            # 其他消息类型
            else:
                logger.info(f"未处理消息类型: {msg_type}")
                response = self.server.channel.reply_text(message, "抱歉，我目前只支持文本消息")
            
            # 发送响应
            self.send_response(200)
            self.send_header('Content-type', 'application/xml')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"处理POST请求异常: {str(e)}", exc_info=True)
            self.send_error(500, "Internal Server Error")


class WechatMpServer(HTTPServer):
    """
    微信公众号HTTP服务器
    """
    def __init__(self, server_address, channel):
        # 增加允许地址重用选项，避免重启时出现"地址已在使用"错误
        self.allow_reuse_address = True
        # 设置请求队列大小
        self.request_queue_size = 10
        # 设置超时时间
        self.timeout = 20
        super().__init__(server_address, WechatMpRequestHandler)
        self.channel = channel
    
    def handle_error(self, request, client_address):
        """
        重写错误处理方法，优雅处理服务器异常
        """
        # 提取客户端IP
        client_ip = client_address[0] if client_address else "未知"
        
        # 获取异常信息
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # 过滤常见网络异常，不记录日志
        if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return
        
        # 对于其他异常，记录简化的错误信息
        logger.error(f"处理来自 {client_ip} 的请求时发生异常: {exc_type.__name__}: {exc_value}")


class WechatMpChannel:
    """
    微信公众号通道
    """
    def __init__(self, bot):
        """
        初始化微信公众号通道
        :param bot: 机器人实例
        """
        self.bot = bot
        self.token = get_value("wechat_mp_token")
        self.app_id = get_value("wechat_mp_app_id")
        self.app_secret = get_value("wechat_mp_app_secret")
        self.aes_key = get_value("wechat_mp_aes_key")
        self.port = get_value("wechat_mp_port", 80)
        self.address = get_value("wechat_mp_address", "0.0.0.0")
        self.auth_mode = get_value("wechat_mp_auth_mode", "plain")
        self.async_timeout = get_value("async_process_timeout", 5)
        self.running = False
        self.subscribe_msg = get_value("subscribe_msg", "感谢关注！")
        self.server = None
        self.server_thread = None
        
        # 验证配置
        if not self.token or self.token == "YOUR_WECHAT_TOKEN":
            logger.error("微信Token未设置，请在config.json中配置wechat_mp_token")
        
        # 记录配置信息
        logger.info(f"微信公众号配置 - 认证模式: {self.auth_mode}, IP: {self.address}, 端口: {self.port}")
        logger.info(f"微信公众号认证信息 - Token设置: {'已设置' if self.token else '未设置'}, AppID: {self.app_id}")
    
    def startup(self):
        """
        启动微信公众号服务
        """
        server_address = (self.address, self.port)
        
        try:
            self.server = WechatMpServer(server_address, self)
            
            # 改为使用日志，不直接打印到终端
            logger.info(f"微信公众号服务启动，监听地址: {self.address}:{self.port}")
            logger.debug(f"认证模式: {self.auth_mode}")
            logger.debug(f"Token配置: {self.token[:4]}..." if self.token else "未配置")
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            logger.info("微信公众号服务器线程已启动")
            
            # 主线程保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("接收到终止信号，关闭服务器...")
                self.server.shutdown()
                self.server.server_close()
                logger.info("微信公众号服务器已关闭")
        
        except socket.error as e:
            logger.error(f"启动服务器失败，端口可能被占用: {str(e)}")
            print(f"\n[错误] 启动服务器失败: {str(e)}")
            print(f"请检查端口 {self.port} 是否已被占用\n")
            return False
        
        except Exception as e:
            logger.error(f"启动微信公众号服务异常: {str(e)}", exc_info=True)
            print(f"\n[错误] 启动服务失败: {str(e)}\n")
            return False
    
    def handle_message(self, message):
        """
        处理微信消息
        :param message: 微信消息内容
        :return: 回复内容
        """
        try:
            msg_type = message.get("MsgType", "text")
            from_user = message.get("FromUserName", "")
            to_user = message.get("ToUserName", "")
            content = message.get("Content", "")
            event = message.get("Event", "")
            
            logger.info(f"收到微信消息: FromUser={from_user}, MsgType={msg_type}, Event={event}, Content={content}")
            
            # 关注事件
            if msg_type == "event" and event.lower() == "subscribe":
                return self.handle_subscribe_event(from_user, to_user)
            
            # 文本消息
            if msg_type == "text":
                return self.handle_text_message(message)
            
            # 语音消息
            if msg_type == "voice":
                recognition = message.get("Recognition", "")
                if recognition:
                    return self.handle_text_message(message)
                else:
                    return self.reply_text(message, "抱歉，我无法识别您的语音")
            
            # 其他类型的消息
            logger.info(f"收到未处理的消息类型: {msg_type}")
            return self.reply_text(message, "抱歉，我目前只支持文本对话")
        
        except Exception as e:
            logger.error(f"处理微信消息异常: {str(e)}", exc_info=True)
            return self.reply_text(message, "处理消息出错，请稍后再试")
    
    def handle_subscribe_event(self, from_user, to_user):
        """
        处理关注事件
        :param from_user: 发送方用户ID
        :param to_user: 接收方用户ID
        :return: 回复内容
        """
        logger.info(f"新用户关注: {from_user}")
        
        # 构建一个模拟消息字典
        message = {
            'FromUserName': from_user,
            'ToUserName': to_user,
            'MsgType': 'event',
            'Event': 'subscribe'
        }
        
        return self.reply_text(message, self.subscribe_msg)
    
    def handle_text_message(self, message):
        """
        处理文本消息
        :param message: 消息字典
        :return: 回复消息
        """
        content = message.get('Content', '')
        msg_id = message.get('MsgId', 'unknown')
        user_id = message.get('FromUserName', '')
        
        # 构建会话ID
        session_id = self._build_session_id(message)
        
        # 定义回调函数，用于发送消息给用户
        def send_reply_callback(session_id, reply_content):
            # 从会话ID中提取用户ID
            if ":" in session_id:
                openid = session_id.split(":", 1)[1]
            else:
                openid = session_id
            # 发送消息给用户
            self.send_text_to_user(openid, reply_content)
        
        # 异步回复，传递回调函数
        result = self.bot.reply_async(session_id, content, callback=send_reply_callback)
        
        if result.get("success"):
            # 返回空消息，不显示"收到消息，正在思考中..."
            return self.reply_empty(message)
        else:
            return self.reply_text(message, f"处理消息失败: {result.get('message', '未知错误')}")
    
    def handle_voice_message(self, message):
        """
        处理语音消息
        :param message: 消息字典
        :return: 回复消息
        """
        recognition = message.get("Recognition", "")
        if recognition:
            print(f"[语音识别结果] {recognition}")
            # 将语音识别结果作为文本处理
            return self.handle_text_message(message)
        else:
            return self.reply_text(message, "抱歉，我无法识别您的语音")
    
    def reply_text(self, message, content):
        """
        回复文本消息
        :param message: 消息字典
        :param content: 消息内容
        :return: 回复的XML
        """
        response = f"""<xml>
<ToUserName><![CDATA[{message['FromUserName']}]]></ToUserName>
<FromUserName><![CDATA[{message['ToUserName']}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""
        return response
    
    def reply_empty(self, message):
        """
        回复空消息（无内容）
        :param message: 消息字典
        :return: 回复的XML
        """
        response = f"""<xml>
<ToUserName><![CDATA[{message['FromUserName']}]]></ToUserName>
<FromUserName><![CDATA[{message['ToUserName']}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[]]></Content>
</xml>"""
        return response
    
    def send_text_to_user(self, openid, content):
        """
        主动发送文本消息给用户
        :param openid: 用户openid
        :param content: 文本内容
        :return: 发送结果
        """
        # 记录回复信息
        logger.info(f"[AI回复] {content}")
        
        # 使用微信客户端API发送消息
        try:
            from channel.wechat_mp_client import mp_client
            result = mp_client.send_text_message(openid, content)
            if result:
                logger.info(f"已发送回复给用户: {openid[:8]}...")
            else:
                logger.error(f"发送回复给用户失败: {openid[:8]}...")
            return result
        except Exception as e:
            logger.error(f"发送消息给用户失败: {str(e)}")
            return False

    def _build_session_id(self, message):
        """
        构建会话ID
        :param message: 消息字典
        :return: 会话ID
        """
        from_user = message.get('FromUserName', '')
        return f"wechat_mp:{from_user}"

    def _parse_xml_to_dict(self, xml_string):
        """
        解析XML字符串为字典
        :param xml_string: XML字符串
        :return: 字典
        """
        message = {}
        
        # 提取常见字段
        pattern_map = {
            'ToUserName': r'<ToUserName><!\[CDATA\[(.*?)\]\]></ToUserName>',
            'FromUserName': r'<FromUserName><!\[CDATA\[(.*?)\]\]></FromUserName>',
            'CreateTime': r'<CreateTime>(.*?)</CreateTime>',
            'MsgType': r'<MsgType><!\[CDATA\[(.*?)\]\]></MsgType>',
            'Content': r'<Content><!\[CDATA\[(.*?)\]\]></Content>',
            'MsgId': r'<MsgId>(.*?)</MsgId>',
            'Event': r'<Event><!\[CDATA\[(.*?)\]\]></Event>',
            'Recognition': r'<Recognition><!\[CDATA\[(.*?)\]\]></Recognition>'
        }
        
        for key, pattern in pattern_map.items():
            match = re.search(pattern, xml_string)
            if match:
                message[key] = match.group(1)
        
        return message 