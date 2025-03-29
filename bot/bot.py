import json
import time
import requests
import threading
import re
from common.log import logger
from common.utils import generate_request_id, async_run
from config import get_value

class DeepSeekBot:
    """
    DeepSeek机器人，用于调用阿里云百炼的DeepSeek-R1 API
    """
    def __init__(self):
        self.api_key = get_value("open_ai_api_key")
        self.api_base = get_value("open_ai_api_base")
        self.proxy = get_value("proxy")
        self.model = get_value("model", "deepseek-r1")
        self.character_desc = get_value("character_desc", "")
        self.conversation_max_tokens = get_value("conversation_max_tokens", 1000)
        self.conversations = {}
        self.lock = threading.RLock()
        self.api_timeout = get_value("api_timeout", 60)
        self.max_retries = get_value("api_max_retries", 2)
        self.bailian_app_id = get_value("bailian_app_id", "")
        
        if self.model == "bailian-app" and not self.bailian_app_id:
            logger.error("使用百炼应用模式但未设置应用ID，请在config.json中配置bailian_app_id")
        
        if self.character_desc:
            logger.info(f"机器人初始化，人设描述已配置，长度: {len(self.character_desc)}")
        else:
            logger.warning("人设描述为空，请在config.json中配置character_desc")
        
        if not self.api_key or self.api_key == "YOUR_API_KEY":
            logger.error("API Key未设置，请在config.json中配置open_ai_api_key")

    def calculate_timeout(self, message):
        """
        根据消息长度和复杂度动态计算合理的超时时间
        """
        base_timeout = self.api_timeout
        msg_length = len(message)
        
        # 针对较长消息增加超时时间
        if msg_length > 200:
            # 每增加100字符增加5秒超时，但最多增加30秒
            additional_timeout = min(30, (msg_length - 200) // 100 * 5)
            return base_timeout + additional_timeout
        
        return base_timeout

    def create_session(self, session_id):
        """创建会话"""
        with self.lock:
            if session_id not in self.conversations:
                self.conversations[session_id] = {
                    "session_id": session_id,
                    "messages": []
                }
                # 添加系统消息
                if self.character_desc and len(self.character_desc.strip()) > 0:
                    # 添加长度限制提示
                    system_prompt = f"{self.character_desc}\n\n注意：你的回复会在微信公众号显示，过长的回复将被自动分段发送。如果可能，尽量控制单次回复长度在2000字以内，但不要因此牺牲回答质量。"
                    self.conversations[session_id]["messages"].append({
                        "role": "system",
                        "content": system_prompt
                    })
                    logger.debug(f"为会话 {session_id} 添加系统消息(人设)")
            
            # 确保会话有系统消息
            session = self.conversations[session_id]
            has_system_message = any(msg["role"] == "system" for msg in session["messages"])
            
            if not has_system_message and self.character_desc and len(self.character_desc.strip()) > 0:
                # 添加长度限制提示
                system_prompt = f"{self.character_desc}\n\n注意：你的回复会在微信公众号显示，过长的回复将被自动分段发送。如果可能，尽量控制单次回复长度在2000字以内，但不要因此牺牲回答质量。"
                session["messages"].insert(0, {
                    "role": "system",
                    "content": system_prompt
                })
            
            return self.conversations[session_id]

    def get_session(self, session_id):
        """获取会话"""
        with self.lock:
            return self.create_session(session_id)

    def add_message(self, session_id, message):
        """添加消息到会话"""
        with self.lock:
            session = self.create_session(session_id)
            session["messages"].append(message)
            
            # 限制会话长度，保持在最大token限制内
            self._trim_conversation(session)
            
            return session
    
    def _trim_conversation(self, session):
        """
        清理会话历史，保持在token限制内
        保留系统消息和最近的用户消息和AI回复
        """
        messages = session["messages"]
        
        # 如果消息数量少于3，不需要清理
        if len(messages) < 3:
            return
            
        # 分离系统消息和其他消息
        system_messages = [msg for msg in messages if msg["role"] == "system"]
        other_messages = [msg for msg in messages if msg["role"] != "system"]
        
        # 计算大致的token数量
        # 这是一个简化的估计，每个字符大约0.5-1个token
        total_chars = sum(len(msg["content"]) for msg in messages)
        estimated_tokens = total_chars * 0.7  # 简单估计
        
        # 如果预估token数量超过限制，删除较早的非系统消息
        while estimated_tokens > self.conversation_max_tokens and len(other_messages) > 4:
            # 每次删除一对对话（用户消息和助手回复）
            if len(other_messages) >= 2:
                other_messages.pop(0)  # 删除最早的消息
                if other_messages and other_messages[0]["role"] == "assistant":
                    other_messages.pop(0)  # 如果下一条是助手回复，也删除
            else:
                # 如果只剩下一条非系统消息，则停止删除
                break
                
            # 重新计算token估计
            total_chars = sum(len(msg["content"]) for msg in system_messages) + sum(len(msg["content"]) for msg in other_messages)
            estimated_tokens = total_chars * 0.7
        
        # 重建会话消息列表，保持系统消息在最前面
        session["messages"] = system_messages + other_messages

    def send_to_api(self, messages, timeout):
        """
        发送请求到API
        :param messages: 消息列表
        :param timeout: 超时时间
        :return: (成功标志, 结果或错误信息)
        """
        # 准备请求数据
        if self.model == "bailian-app":
            # 百炼应用请求格式
            data = {
                "model": self.model,
                "messages": messages,
                "parameters": {
                    "app_id": self.bailian_app_id,  # 百炼应用ID
                    "stream": False
                }
            }
            api_endpoint = f"{self.api_base}/chat/completions"
        else:
            # 通义千问兼容模式
            data = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 0.95
            }
            api_endpoint = f"{self.api_base}/chat/completions"
        
        # 设置代理
        proxies = None
        if self.proxy:
            proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
        
        # 记录开始时间
        start_time = time.time()
        
        # 重试逻辑
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                # 发送请求
                response = requests.post(
                    api_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json=data,
                    proxies=proxies,
                    timeout=timeout
                )
                
                # 如果成功，返回结果
                if response.status_code == 200:
                    result = response.json()
                    reply_content = result["choices"][0]["message"]["content"].strip()
                    
                    # 计算耗时
                    elapsed_time = time.time() - start_time
                    logger.info(f"API响应成功，耗时: {elapsed_time:.2f}秒")
                    
                    return True, reply_content
                
                # 状态码不是200，记录错误继续重试
                error_msg = f"API请求失败: HTTP {response.status_code}, {response.text}"
                logger.warning(f"{error_msg}, 第{retry_count+1}次重试")
                
            except requests.exceptions.Timeout:
                # 超时后增加重试计数
                error_msg = "请求超时"
                logger.warning(f"{error_msg}, 第{retry_count+1}次重试")
                
            except Exception as e:
                # 其他异常
                error_msg = f"请求异常: {str(e)}"
                logger.error(f"{error_msg}, 第{retry_count+1}次重试")
            
            # 增加重试计数
            retry_count += 1
            
            # 如果已经达到最大重试次数，跳出循环
            if retry_count > self.max_retries:
                break
            
            # 退避策略：每次等待时间加倍
            wait_time = retry_count * 2
            logger.info(f"等待{wait_time}秒后重试")
            time.sleep(wait_time)
        
        # 所有重试都失败了
        return False, "API请求失败，无法获取回复"

    def reply(self, session_id, message):
        """
        同步回复消息
        :param session_id: 会话ID
        :param message: 用户消息
        :return: 回复内容
        """
        request_id = generate_request_id()
        logger.info(f"API请求: [{request_id}] {message}")
        
        # 提取用户ID（对于微信用户，用户ID就是openid部分）
        user_id = session_id
        if ":" in session_id:
            user_id = session_id.split(":", 1)[1]
        
        # 获取会话
        session = self.get_session(session_id)
        
        # 添加用户消息到会话
        self.add_message(session_id, {"role": "user", "content": message})
        
        # 准备请求数据
        messages = session["messages"].copy()
        
        # 计算动态超时时间
        dynamic_timeout = self.calculate_timeout(message)
        
        # 发送请求到API
        success, result = self.send_to_api(messages, dynamic_timeout)
        
        if success:
            # 添加助手回复到会话
            self.add_message(session_id, {"role": "assistant", "content": result})
            return result
        else:
            logger.error(f"API请求失败: {result}")
            return f"很抱歉，无法获取回复。错误: {result}"

    def reply_async(self, session_id, message, callback=None):
        """
        异步回复，立即返回，后台处理
        :param session_id: 会话ID
        :param message: 用户消息
        :param callback: 回调函数，处理完成后调用
        :return: 状态信息
        """
        def process_async_reply():
            try:
                reply = self.reply(session_id, message)
                # 如果有回调函数，调用它
                if callback:
                    callback(session_id, reply)
                logger.info(f"异步回复完成: {session_id}")
                return reply
            except Exception as e:
                logger.error(f"异步回复处理异常: {str(e)}")
                # 如果出错，也尝试调用回调
                if callback:
                    callback(session_id, f"处理请求时发生错误: {str(e)}")
                return None
        
        # 启动异步线程
        async_run(process_async_reply)
        
        return {
            "success": True,
            "message": "正在处理中"
        }