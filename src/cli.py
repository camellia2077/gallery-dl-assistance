# src/cli.py

import argparse
from typing import Any, Dict

# 程序版本号
VERSION = '0.1.0'

def parse_args() -> Dict[str, Any]:
    """
    解析命令行参数，并返回一个包含解析结果的字典。
    """
    parser = argparse.ArgumentParser(description="Bilibili 动态图片下载助手")
    
    # --- 1. --version 参数 ---
    parser.add_argument('-v', '--version', action='version', 
                        version=f'Bilibili Downloader v{VERSION}',
                        help='显示当前程序的版本号')
    
    # --- 2. 下载功能参数 ---
    parser.add_argument('-u', '--uid', type=int, 
                        help='单独下载指定的用户ID（将忽略配置文件中的用户列表）')
    
    parser.add_argument('-n', '--name', type=str, 
                        help='指定用户的自定义文件夹名称（仅在指定 -u/--uid 时有效）。如果不指定，将尝试查找本地已有文件夹或使用 API 获取的名称。')
    
    # 3. 解析参数
    args = parser.parse_args()
    
    # 将解析结果转换为字典返回
    return vars(args)