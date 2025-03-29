from PIL import Image
import sys

def convert_to_ico(input_file, output_file):
    """
    将JPG文件转换为ICO格式
    :param input_file: 输入文件路径
    :param output_file: 输出文件路径
    """
    try:
        # 打开图像文件
        img = Image.open(input_file)
        
        # 调整大小为标准图标尺寸
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
        img = img.resize((256, 256), Image.LANCZOS)
        
        # 保存为ico格式
        img.save(output_file, format='ICO', sizes=icon_sizes)
        
        print(f"转换成功: {input_file} -> {output_file}")
        return True
    except Exception as e:
        print(f"转换失败: {e}")
        return False

if __name__ == "__main__":
    input_file = "b_2c9004e0db255943ebd53561315853a5.jpg"
    output_file = "app_icon.ico"
    convert_to_ico(input_file, output_file) 