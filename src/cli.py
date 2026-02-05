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

    # --- 3. 【新增】失败重试控制参数 ---
    # 使用互斥组，确保不能同时指定开启和关闭
    retry_group = parser.add_mutually_exclusive_group()
    
    # dest='retry_failed' 确保这两个参数都映射到字典的同一个 key 上
    # default=None 非常关键，表示如果用户不传，值为 None (这样 main.py 就会去读配置文件)
    retry_group.add_argument('--retry', action='store_true', dest='retry_failed', default=None,
                        help='强制开启失败重试功能（覆盖配置文件）')
    
    retry_group.add_argument('--no-retry', action='store_false', dest='retry_failed', default=None,
                        help='强制关闭失败重试功能（覆盖配置文件）')
    
    # 4. 解析参数
    args = parser.parse_args()
    
    # 将解析结果转换为字典返回
    return vars(args)