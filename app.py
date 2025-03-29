#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import ctypes
import atexit
import time
from common.log import logger, init_logger
from config import get_value, load_config, config

# 全局变量保存对托盘图标的引用
tray_icon_ref = None

try:
    import app_icons
except ImportError:
    pass

def signal_handler(sig, frame):
    """
    信号处理函数，用于优雅退出
    :param sig: 信号
    :param frame: 栈帧
    """
    logger.info("收到退出信号，正在关闭服务...")
    # 写入退出信号
    with open("wechat.pid", "w") as f:
        f.write("stop")
    sys.exit(0)

# Windows控制台关闭处理函数
def handle_windows_console_close(event):
    if event == 0:  # CTRL_CLOSE_EVENT
        logger.info("控制台窗口被关闭，程序将在后台继续运行...")
        # 返回True表示我们处理了这个事件，不需要系统默认处理
        return True
    return False

def cleanup():
    """
    退出前的清理操作
    """
    logger.info("程序正常退出，进行清理...")
    try:
        with open("wechat.pid", "w") as f:
            f.write("stop")
    except Exception as e:
        logger.error(f"清理操作失败: {str(e)}")

def main():
    """
    主函数
    """
    global tray_icon_ref
    
    # 注册清理函数
    atexit.register(cleanup)
    
    # 在Windows下处理控制台关闭事件
    if os.name == 'nt':
        try:
            # 设置控制台控制处理器
            handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
            handler = handler_type(handle_windows_console_close)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)
            logger.debug("已注册控制台关闭事件处理")
        except Exception as e:
            logger.error(f"注册控制台关闭事件处理失败: {str(e)}")
    
    # 加载配置
    config_data = load_config()
    
    # 确保日志目录存在
    log_dir = get_value("log_dir", "logs")
    ensure_log_dir(log_dir)
    
    # 初始化日志
    log_level = get_value("log_level", "info")
    init_logger(log_dir, log_level)
    
    # 降低HTTP相关库的日志级别
    import logging
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("http.server").setLevel(logging.ERROR)
    
    # 在日志初始化后再设置图标，确保日志可用
    try:
        if 'app_icons' in sys.modules:
            # 初始化图标，并保存对托盘图标的引用
            app_icons.init_icons()
            tray_icon_ref = app_icons.tray_icon
            logger.debug(f"托盘图标初始化: {'成功' if tray_icon_ref else '失败'}")
            
            # 如果是从桌面启动的，额外等待一下以确保托盘图标显示
            if os.path.basename(sys.argv[0]).lower() == 'wechat-deepseek.exe':
                logger.debug("从可执行文件启动，等待托盘图标初始化...")
                time.sleep(1)  # 额外等待时间
    except Exception as e:
        logger.error(f"初始化图标失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
    
    # 显示关键配置信息
    logger.info("======== 微信AI助手服务启动 ========")
    logger.debug(f"服务地址: {get_value('wechat_mp_address', '0.0.0.0')}:{get_value('wechat_mp_port', 80)}")
    logger.debug(f"认证方式: {get_value('wechat_mp_auth_mode', 'compatible')}")
    logger.debug(f"API基础URL: {get_value('open_ai_api_base', '未配置')}")
    logger.info(f"使用模型: {get_value('model', 'deepseek-r1')}")
    logger.info("====================================")
    
    # 只有在配置加载完成后才导入依赖模块
    from channel.wechat_mp_channel import WechatMpChannel
    from bot.bot import DeepSeekBot
    
    # 创建机器人实例
    bot = DeepSeekBot()
    
    # 创建微信公众号通道
    channel_type = get_value("channel_type")
    if channel_type == "wechat_mp_service":
        channel = WechatMpChannel(bot)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动服务
        channel.startup()
    else:
        logger.error(f"不支持的频道类型: {channel_type}")

def ensure_log_dir(log_dir):
    """
    确保日志目录存在
    :param log_dir: 日志目录
    """
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception as e:
            print(f"创建日志目录失败: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main() 