import json
import time
import requests
import threading
import traceback
from common.log import logger
from config import get_value, config

class WechatMpClient:
    """
    微信公众号客服消息接口客户端
    用于发送消息给用户
    """
    def __init__(self):
        # 直接从全局配置读取，避免任何潜在的字典键获取问题
        try:
            self.app_id = str(config.get("wechat_mp_app_id", "")).strip()
            self.app_secret = str(config.get("wechat_mp_app_secret", "")).strip()
            logger.info(f"微信公众号配置: AppID长度={len(self.app_id)}, AppSecret长度={len(self.app_secret)}")
        except Exception as e:
            logger.error(f"读取微信公众号配置异常: {str(e)}")
            self.app_id = ""
            self.app_secret = ""
        
        self.access_token = None
        self.token_expire_time = 0
        self.lock = threading.RLock()
        self.proxy = get_value("proxy", "")
        
        # 微信单条消息最大长度
        self.max_message_length = 2000
        
        # 简化判断逻辑
        self.enabled = bool(self.app_id and self.app_secret)
        if not self.enabled:
            logger.warning("微信公众号客服消息接口未配置或配置无效，消息发送将不可用")
    
    def get_access_token(self):
        """
        获取微信接口调用的access_token
        :return: access_token
        """
        if not self.enabled:
            return None
            
        with self.lock:
            # 检查现有token是否有效
            if self.access_token and time.time() < self.token_expire_time - 60:
                return self.access_token
            
            # 获取新token
            try:
                url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
                
                # 设置代理
                proxies = None
                if self.proxy:
                    proxies = {
                        "http": self.proxy,
                        "https": self.proxy
                    }
                
                response = requests.get(url, proxies=proxies, timeout=10)
                
                if response.status_code != 200:
                    logger.error(f"获取微信access_token失败: HTTP {response.status_code}, {response.text}")
                    return None
                
                result = response.json()
                if "access_token" in result:
                    self.access_token = result["access_token"]
                    # 设置过期时间，提前5分钟刷新
                    self.token_expire_time = time.time() + result.get("expires_in", 7200) - 300
                    logger.info(f"获取微信access_token成功: {self.access_token[:10]}...")
                    return self.access_token
                else:
                    logger.error(f"获取微信access_token失败: {result.get('errmsg', '未知错误')}")
                    return None
            
            except Exception as e:
                logger.error(f"获取微信access_token异常: {str(e)}")
                logger.error(traceback.format_exc())
                return None
    
    def split_message(self, content):
        """
        智能拆分长消息，保持语义完整性
        :param content: 原始消息内容
        :return: 拆分后的消息列表
        """
        # 微信公众号单条消息上限约2000字符，留出余量设置为1800
        max_length = 1800
        
        # 如果消息足够短，不需要拆分
        if len(content) <= max_length:
            return [content]
            
        parts = []
        remaining = content
        
        # 段落分隔符优先级
        separators = [
            "\n\n",  # 段落分隔符，优先级最高
            "\n",    # 换行符
            "。",    # 句号
            "！",    # 感叹号
            "？",    # 问号
            "；",    # 分号
            "，",    # 逗号
            " ",     # 空格
            ".",     # 英文句号
            ";",     # 英文分号
            ","      # 英文逗号
        ]
        
        while remaining:
            if len(remaining) <= max_length:
                parts.append(remaining)
                break
                
            # 在最大长度范围内寻找最佳切分点
            cut_index = -1
            
            for separator in separators:
                # 从后向前查找最后一个分隔符
                pos = remaining[:max_length].rfind(separator)
                if pos > 0:  # 找到了有效分隔符
                    cut_index = pos + len(separator)  # 包含分隔符
                    break
            
            # 如果找不到任何分隔符，就在最大长度处截断
            if cut_index == -1:
                cut_index = max_length
                
            # 截取当前部分并添加到结果列表
            parts.append(remaining[:cut_index])
            
            # 更新剩余内容
            remaining = remaining[cut_index:]
            
        # 添加序号标识，让用户知道这是分段回复
        for i, part in enumerate(parts):
            if len(parts) > 1:
                # 添加更明显的分段标记
                parts[i] = f"[{i+1}/{len(parts)}] {part}"
                
        return parts
    
    def _send_single_message(self, openid, content):
        """
        发送单条消息的核心实现
        :param openid: 用户openid
        :param content: 消息内容
        :return: 发送结果
        """
        if not self.enabled:
            logger.warning("微信公众号客服消息接口未配置，跳过发送")
            return False
        
        access_token = self.get_access_token()
        if not access_token:
            logger.error("获取access_token失败，无法发送客服消息")
            return False
        
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
            
            # 确保内容长度不超过限制
            if len(content) > self.max_message_length:
                logger.warning(f"单条消息长度({len(content)})超过限制({self.max_message_length})，将被截断")
                content = content[:self.max_message_length-3] + "..."
            
            data = {
                "touser": openid,
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            # 设置代理
            proxies = None
            if self.proxy:
                proxies = {
                    "http": self.proxy,
                    "https": self.proxy
                }
            
            # 禁用ASCII编码，确保中文不会被转为Unicode转义序列
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            headers = {'Content-Type': 'application/json; charset=utf-8'}
            
            # 使用重试机制
            max_retries = 3  # 增加重试次数
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    response = requests.post(url, data=json_data, headers=headers, proxies=proxies, timeout=10)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("errcode", 0) == 0:
                            return True
                        else:
                            err_code = result.get("errcode")
                            err_msg = result.get("errmsg", "未知错误")
                            logger.warning(f"发送微信客服消息失败: 错误码={err_code}, 错误信息={err_msg}")
                            
                            # 针对特定错误码处理
                            if err_code == 45015:  # 回复时间超过限制
                                logger.error("发送失败：回复超时，无法继续发送")
                                return False  # 这种情况不再重试
                            elif err_code == 45002:  # 消息长度超过限制
                                # 这种情况应该在拆分阶段处理，这里做最后保险
                                if len(content) > 1000:
                                    content = content[:1000] + "...(内容已截断)"
                                    json_data = json.dumps({
                                        "touser": openid,
                                        "msgtype": "text",
                                        "text": {"content": content}
                                    }, ensure_ascii=False).encode('utf-8')
                                    logger.warning("消息长度超限，已强制截断重试")
                                    continue
                    else:
                        logger.warning(f"发送微信客服消息HTTP错误: {response.status_code}")
                    
                    # 重试逻辑
                    retry_count += 1
                    if retry_count <= max_retries:
                        # 等待时间递增
                        wait_time = retry_count * 2  # 增加等待时间
                        logger.info(f"等待{wait_time}秒后重试发送微信消息")
                        time.sleep(wait_time)
                
                except Exception as e:
                    logger.error(f"发送消息请求异常: {str(e)}")
                    retry_count += 1
                    if retry_count <= max_retries:
                        wait_time = retry_count * 2
                        logger.info(f"等待{wait_time}秒后重试")
                        time.sleep(wait_time)
            
            logger.error(f"发送消息失败，已达最大重试次数({max_retries})")
            return False
            
        except Exception as e:
            logger.error(f"发送微信客服消息异常: {str(e)}")
            return False
    
    def send_text_message(self, openid, content):
        """
        发送文本消息，自动处理长消息拆分
        :param openid: 用户openid
        :param content: 消息内容
        :return: 发送结果
        """
        if not self.enabled:
            logger.warning("微信公众号客服消息接口未配置，跳过发送")
            return False
            
        if not openid:
            logger.error(f"发送微信客服消息参数无效: openid为空")
            return False
            
        # 确保有内容发送
        if not content or content.strip() == "":
            content = "抱歉，AI处理您的问题时遇到了困难，请换个方式提问或稍后再试。"
            logger.warning(f"消息内容为空，使用默认回复: {content}")
        
        # 检查消息长度，如果超过限制就拆分
        if len(content) > 1800:  # 设置一个更保守的阈值
            logger.info(f"消息长度({len(content)})超过限制(1800)，将拆分为多条消息")
            message_parts = self.split_message(content)
            
            # 发送拆分后的每一部分
            all_success = True
            for part in message_parts:
                part_success = self._send_single_message(openid, part)
                if not part_success:
                    all_success = False
                    logger.warning(f"分段消息发送失败 (总共{len(message_parts)}段)")
                
                # 每条消息之间稍微等待，避免发送太快
                if len(message_parts) > 1:
                    time.sleep(1)  # 增加等待时间，降低被限制的风险
            
            if len(message_parts) > 1:
                logger.info(f"分段消息发送完成，共{len(message_parts)}条")
            
            return all_success
        else:
            # 消息长度在限制内，直接发送
            return self._send_single_message(openid, content)

# 创建全局客户端实例
mp_client = WechatMpClient() 