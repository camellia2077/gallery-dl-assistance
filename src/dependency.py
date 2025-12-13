# src/dependency.py

import shutil
import sys

def check_dependencies():
    """
    检查程序运行所需的外部依赖是否存在。
    如果缺少关键依赖，打印友好的错误信息并退出程序。
    """
    _check_gallery_dl()
    # 未来如果有 ffmpeg 依赖，也可以在这里添加: _check_ffmpeg()

def _check_gallery_dl():
    """检查 gallery-dl 是否安装且在 PATH 中。"""
    # shutil.which 会在系统 PATH 中查找可执行文件
    # Windows 下会自动寻找 gallery-dl.exe
    if shutil.which("gallery-dl") is None:
        print("\n" + "=" * 50)
        print(" [严重错误] 未找到核心依赖: gallery-dl")
        print("=" * 50)
        print("  本程序依赖 'gallery-dl' 来解析 Bilibili 数据。")
        print("  检测到您的系统中未安装它，或未添加到环境变量 PATH 中。")
        print("\n  解决方法:")
        print("  1. 请在终端运行: pip install gallery-dl")
        print("  2. 如果已安装，请确保 Python 的 Scripts 目录在系统环境变量 Path 中。")
        print("=" * 50 + "\n")
        sys.exit(1) # 返回非零状态码表示异常退出