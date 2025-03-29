import os
import sys
import threading
import io
import base64
from common.log import logger
from PIL import Image, ImageDraw

# 嵌入用户提供的JPG图标数据（base64编码）
# 这里替换为实际的b_2c9004e0db255943ebd53561315853a5.jpg的base64数据
JPG_ICON_DATA = """
/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCABAAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD0LwlfeObe1nt/D1vpL28stu0ZuzKD8rrljhcA4JH1HatL/hZHj3/oB6J/3/l/+JrhvCyQz/ES2sbK7W1uLlVt1YkAOy5RR0OQSQPStHXvClxf+MNQt7fS0j1S1EZYwoHjeMBwyrgEYOR+Z9KAPRbbxj4uuIhIdE0oKSQMTyHOOv8AAtTf8LI8e/8AQD0T/v8Ay/8AxNcp4M8I6sNdF9qYuLWxWMqPOB82Rgdl6hQARnHJx7Z9AudGurnxzY6pHpyQW0VobWWTeMSL8xK4znByp/L1oAp/8LI8e/8AQD0T/v8Ay/8AxNdP4P1rxtq+pw2+o6Xpcdq0bM8msgcEDgY2HrxWBqGjz3nx6sbWO1CXVvGsjxhQGKtCxLDHXAOffpXoPgP/ka9K/65yf8AoBqbuyA7uiiimAUUUUAcV4AJOo6rIQVZ7okMDkHBPSsP4leFtZuNXGraTBJdQyRqksUQyzBei46nHTPpj0rt/DMTJqWqFkI3XTEcehNdLRcCjo9o9lpVpbyY8yKFUfAwNwGB+tXqKKACiiigD//Z
"""

# 判断是否是打包后的可执行文件
def is_frozen():
    return getattr(sys, 'frozen', False)

# 获取桌面路径
def get_desktop_path():
    if os.name == 'nt':
        return os.path.join(os.path.expanduser('~'), 'Desktop')
    return os.path.expanduser('~/Desktop')

# 获取程序路径
def get_app_path():
    if is_frozen():
        return os.path.abspath(sys.executable)
    else:
        return os.path.abspath(__file__)

# 获取图标图像 - 直接从内置JPG加载
def get_icon_image():
    try:
        # 获取程序所在目录 - 优先使用可执行文件目录
        if is_frozen():
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 使用绝对路径
        jpg_path = os.path.join(base_dir, "b_2c9004e0db255943ebd53561315853a5.jpg")
        jpg_path = os.path.abspath(jpg_path)
        
        # 记录当前工作目录，帮助调试
        logger.debug(f"当前工作目录: {os.getcwd()}")
        logger.debug(f"图标路径: {jpg_path}")
        
        # 加载图标 - 优先从文件加载，失败则使用内置
        if os.path.exists(jpg_path):
            logger.debug(f"从文件加载图标: {jpg_path}")
            image = Image.open(jpg_path)
        else:
            # 使用内置的JPG数据
            logger.debug(f"使用内置JPG图标 (文件不存在: {jpg_path})")
            jpg_data = base64.b64decode(JPG_ICON_DATA)
            image = Image.open(io.BytesIO(jpg_data))
            
            # 保存到文件系统，方便下次使用
            try:
                with open(jpg_path, 'wb') as f:
                    f.write(jpg_data)
                logger.debug(f"已保存内置图标到: {jpg_path}")
            except Exception as save_err:
                logger.debug(f"保存内置图标失败: {str(save_err)}")
        
        # 处理图像 - 确保为正方形
        width, height = image.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        image = image.crop((left, top, right, bottom))
        
        # 调整大小但保持原始图像比例
        icon_image = image.resize((32, 32), Image.LANCZOS)
        
        return icon_image, jpg_path
    except Exception as e:
        logger.debug(f"加载图标失败: {str(e)}")
        return None, None

# 创建桌面快捷方式
def create_desktop_shortcut():
    if os.name == 'nt':  # 仅适用于Windows
        try:
            import win32com.client
            
            # 获取程序路径和图标路径
            app_path = get_app_path()
            icon_image, jpg_path = get_icon_image()
            
            if not jpg_path:
                logger.debug("未找到图标，无法创建桌面快捷方式")
                return
                
            # 将JPG转为ICO供快捷方式使用
            icon_dir = os.path.dirname(app_path)
            ico_path = os.path.join(icon_dir, "app_icon.ico")
            icon_image.save(ico_path, format='ICO')
            
            # 获取桌面路径
            desktop = get_desktop_path()
            shortcut_path = os.path.join(desktop, "wechat-deepseek.lnk")
            
            # 确保图标文件是绝对路径
            abs_icon_path = os.path.abspath(ico_path)
            
            # 创建快捷方式
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = app_path
            shortcut.WorkingDirectory = os.path.dirname(app_path)  # 确保工作目录正确
            shortcut.IconLocation = abs_icon_path
            shortcut.save()
            
            logger.debug(f"桌面快捷方式已创建/更新，工作目录: {os.path.dirname(app_path)}")
        except Exception as e:
            logger.debug(f"创建桌面快捷方式失败: {str(e)}")

# 设置窗口图标（仅在Windows下有效）
def set_window_icon():
    if os.name == 'nt':  # 仅适用于Windows
        try:
            import ctypes
            import win32gui
            import win32con
            import win32api
            
            # 获取控制台窗口句柄
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            
            if hwnd:
                # 获取图标
                icon_image, jpg_path = get_icon_image()
                if not icon_image:
                    return
                
                # 创建临时ICO文件
                icon_dir = os.path.dirname(get_app_path())
                ico_path = os.path.join(icon_dir, "app_icon.ico")
                icon_image.save(ico_path, format='ICO')
                
                # 加载不同尺寸的图标
                icon_sizes = [16, 32]  # 常用图标尺寸
                icon_handles = []
                
                for size in icon_sizes:
                    try:
                        handle = win32gui.LoadImage(
                            0, ico_path, win32con.IMAGE_ICON,
                            size, size, win32con.LR_LOADFROMFILE
                        )
                        if handle:
                            icon_handles.append((size, handle))
                    except:
                        pass
                
                if icon_handles:
                    # 设置大小图标和小图标
                    for size, handle in icon_handles:
                        if size <= 16:
                            win32api.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, handle)
                        else:
                            win32api.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, handle)
                    
                    logger.debug("窗口图标设置成功")
        except Exception as e:
            logger.debug(f"设置窗口图标失败: {str(e)}")

# 全局变量保存托盘图标引用，防止被垃圾回收
tray_icon = None

# 添加托盘图标
def add_tray_icon():
    if os.name == 'nt':  # 仅适用于Windows
        try:
            import pystray
            import time
            
            # 获取图标
            icon_image, jpg_path = get_icon_image()
            if not icon_image:
                logger.debug("无法获取图标，托盘图标将不会显示")
                return
            
            # 确保ICO文件存在并使用最新图标
            icon_dir = os.path.dirname(get_app_path())
            ico_path = os.path.join(icon_dir, "app_icon.ico")
            ico_path = os.path.abspath(ico_path)
            
            # 确保图标尺寸适合托盘
            tray_icon_image = icon_image.resize((32, 32), Image.LANCZOS)
            tray_icon_image.save(ico_path, format='ICO')
            logger.info(f"托盘图标已保存到: {ico_path}")
            
            # 明确定义退出功能
            def exit_action(icon):
                logger.info("用户点击退出")
                try:
                    with open("wechat.pid", "w") as f:
                        f.write("stop")
                except Exception as e:
                    logger.debug(f"写入退出信号失败: {str(e)}")
                finally:
                    icon.stop()  # 停止图标
                    os._exit(0)  # 确保退出程序
            
            # 创建托盘图标
            icon = pystray.Icon(
                "wechat-deepseek",  # 图标ID
                tray_icon_image,    # 图标图像
                "微信DeepSeek机器人", # 图标悬停文本
                menu=pystray.Menu(
                    pystray.MenuItem("退出", exit_action)
                )
            )
            
            # 在非守护线程中启动托盘图标
            # 这很重要，确保托盘进程不会随主线程退出而结束
            tray_thread = threading.Thread(target=icon.run, daemon=False)
            tray_thread.start()
            
            # 等待一会确保图标显示
            time.sleep(0.5)
            
            logger.info("托盘图标已启动，应该可见")
            return icon  # 返回图标对象以便主程序引用
        except Exception as e:
            logger.error(f"添加托盘图标失败: {str(e)}")
            # 显示详细错误
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None

# 初始化图标设置
def init_icons():
    global tray_icon
    
    # 设置窗口图标
    set_window_icon()
    
    # 添加托盘图标并保存引用
    tray_icon = add_tray_icon()
    
    # 始终更新桌面快捷方式，确保图标一致
    try:
        create_desktop_shortcut()
    except Exception as e:
        logger.debug(f"更新桌面快捷方式失败: {str(e)}") 