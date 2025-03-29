#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import subprocess
import datetime
import atexit

# 配置信息
APP_DIR = os.path.dirname(os.path.abspath(__file__))  # 当前脚本所在目录
APP_SCRIPT = "app.py"
PID_FILE = os.path.join(APP_DIR, "wechat.pid")
LOG_DIR = os.path.join(APP_DIR, "logs")
CHECK_INTERVAL = 60  # 检查间隔(秒)

def get_timestamp():
    """获取当前时间戳，用于日志文件名"""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def is_process_running(pid):
    """检查指定PID的进程是否在运行"""
    try:
        # 在Windows上
        if sys.platform.startswith('win'):
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            return False
        # 在Unix/Linux上
        else:
            os.kill(pid, 0)  # 发送信号0测试进程是否存在
            return True
    except (OSError, ProcessLookupError):
        return False

def is_running():
    """检查微信服务是否在运行"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # 检查进程是否存在
            return is_process_running(pid)
        except (ValueError, IOError):
            return False
    return False

def start_app():
    """启动微信服务"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] 启动微信服务...")
    
    # 创建日志目录(如果不存在)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 当前时间戳，用于日志文件名
    log_file = os.path.join(LOG_DIR, f"wechat_{timestamp}.log")
    
    try:
        # 切换到应用目录
        os.chdir(APP_DIR)
        
        # 使用sys.executable获取当前Python解释器的路径
        python_executable = sys.executable
        print(f"[{timestamp}] 使用Python解释器: {python_executable}")
        
        # 根据操作系统启动进程
        if sys.platform.startswith('win'):
            # Windows系统使用
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                [python_executable, APP_SCRIPT],
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                startupinfo=startupinfo
            )
        else:
            # Unix/Linux系统使用
            process = subprocess.Popen(
                [python_executable, APP_SCRIPT],
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                start_new_session=True  # 相当于nohup，使进程与终端分离
            )
        
        # 将PID保存到文件
        with open(PID_FILE, 'w') as f:
            f.write(str(process.pid))
            
        print(f"[{timestamp}] 微信服务已启动，PID: {process.pid}")
        return True
    except Exception as e:
        print(f"[{timestamp}] 启动失败: {str(e)}")
        return False

def check_and_restart():
    """检查服务并在需要时重启"""
    timestamp = get_timestamp()
    if not is_running():
        print(f"[{timestamp}] 微信服务未运行，开始启动...")
        start_app()
    else:
        print(f"[{timestamp}] 微信服务运行正常")

def monitor_loop():
    """持续监控循环"""
    print(f"[{get_timestamp()}] 开始监控微信服务...")
    try:
        while True:
            check_and_restart()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print(f"[{get_timestamp()}] 监控程序被手动终止")
    finally:
        print(f"[{get_timestamp()}] 监控程序退出")

def cleanup():
    """清理函数，程序退出时调用"""
    print(f"[{get_timestamp()}] 正在清理...")

if __name__ == "__main__":
    # 注册退出时的清理函数
    atexit.register(cleanup)
    
    # 如果是作为启动参数调用
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        if not is_running():
            start_app()
        else:
            print(f"[{get_timestamp()}] 微信服务已在运行中")
        sys.exit(0)
        
    # 执行监控循环
    monitor_loop() 