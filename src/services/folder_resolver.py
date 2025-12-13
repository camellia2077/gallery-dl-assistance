# src/processor/folder_resolver.py

import os
import re
import json
from typing import List, Dict, Any, Optional
from api import BilibiliAPI
from config import Config

class FolderNameResolver:
    """负责确定用户文件夹名称的类。"""

    def __init__(self, base_output_dir: str, api: BilibiliAPI, config: Config):
        self.base_output_dir = base_output_dir
        self.api = api
        self.config = config

    def _sanitize_filename(self, filename: str) -> str:
        """清理字符串，使其可以安全地用作文件名。"""
        # 移除非法字符
        clean_name = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        return clean_name

    def _format_folder_name(self, base_name: str, user_id: int) -> str:
        """
        【新增核心方法】统一格式化文件夹名称规则：Name_UID
        包含智能检测，防止产生 Double UID (例如 Name_123_123)。
        """
        safe_name = self._sanitize_filename(base_name)
        uid_str = str(user_id)
        suffix = f"_{uid_str}"

        # 如果名字已经以 "_UID" 结尾，则不再重复添加
        if safe_name.endswith(suffix):
            return safe_name
        
        return f"{safe_name}{suffix}"

    def _scan_for_folder_by_uid_pattern(self, user_id: int) -> Optional[str]:
        """通过文件夹名称后缀 (_uid) 快速查找现有文件夹。"""
        if not os.path.isdir(self.base_output_dir):
            return None
            
        suffix = f"_{user_id}"
        for folder_name in os.listdir(self.base_output_dir):
            # 严格检查：必须以 _UID 结尾
            if folder_name.endswith(suffix):
                return folder_name
        return None

    def _scan_for_existing_folder(self, user_id: int) -> Optional[str]:
        """(旧版兼容) 深度扫描元数据。"""
        print("  - 警告：正在扫描现有文件夹元数据以匹配用户ID... 这可能需要一些时间。")
        try:
            if not os.path.isdir(self.base_output_dir):
                return None
            for folder_name in os.listdir(self.base_output_dir):
                user_folder = os.path.join(self.base_output_dir, folder_name)
                if not os.path.isdir(user_folder):
                    continue
                meta_dir = os.path.join(user_folder, 'metadata', 'step2')
                if not os.path.isdir(meta_dir):
                    continue
                for meta_file in os.listdir(meta_dir):
                    if not meta_file.endswith('.json'):
                        continue
                    try:
                        with open(os.path.join(meta_dir, meta_file), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if data and isinstance(data, list) and len(data[0]) > 1 and isinstance(data[0][-1], dict):
                           uid_from_meta = data[0][-1].get('detail', {}).get('modules', {}).get('module_author', {}).get('mid')
                           if uid_from_meta and uid_from_meta == user_id:
                               print(f"  - 匹配成功！在文件夹 '{folder_name}' 中找到了用户ID {user_id}。")
                               return folder_name
                    except (json.JSONDecodeError, IndexError, KeyError, TypeError):
                        continue
        except Exception as e:
            print(f"  - 扫描文件夹时出错: {e}")
        return None

    def determine_folder_name_pre_scan(self, user_id: int) -> Optional[str]:
        """用于 Iterative 模式的预扫描。"""
        user_id_str = str(user_id)
        
        # 1. 优先检查配置映射
        if user_id_str in self.config.USER_ID_TO_NAME_MAP:
            mapped_name = self.config.USER_ID_TO_NAME_MAP[user_id_str]
            # 【修改】使用统一格式化方法
            return self._format_folder_name(mapped_name, user_id)

        # 2. 检查本地是否存在符合 Name_UID 格式的文件夹
        existing_by_pattern = self._scan_for_folder_by_uid_pattern(user_id)
        if existing_by_pattern:
            return existing_by_pattern

        # 3. 深度扫描
        return self._scan_for_existing_folder(user_id)

    def determine_folder_name(self, user_id: int, user_page_data: Optional[List[Dict]], post_urls: List[str], first_post_meta: Optional[List[Dict]] = None) -> str:
        """
        确定文件夹名称的主逻辑。
        优先级:
        1. Config 映射 (包含 CLI 传入的名称)
        2. 本地已存在的符合 UID 后缀的文件夹
        3. API 获取的用户名
        4. Fallback (unknown_UID)
        """
        user_id_str = str(user_id)
        base_name = None

        # --- 1. 优先检查配置映射 (CLI传入的名称会在这里被匹配) ---
        if user_id_str in self.config.USER_ID_TO_NAME_MAP:
            base_name = self.config.USER_ID_TO_NAME_MAP[user_id_str]
            print(f"  - [命名] 在配置/命令行中找到强制映射: {user_id_str} -> {base_name}")
            return self._format_folder_name(base_name, user_id)

        # --- 2. 【核心修改】检查本地是否存在符合 Name_UID 格式的文件夹 ---
        # 这一步提到了 API 获取之前。如果本地已经下载过该用户，直接沿用旧文件夹名。
        existing_folder = self._scan_for_folder_by_uid_pattern(user_id)
        if existing_folder:
            print(f"  - [命名] 发现本地已存在匹配 UID 的文件夹，直接使用: {existing_folder}")
            return existing_folder

        # --- 3. 尝试从 API 数据中获取用户名 ---
        print("  - [命名] 本地无记录且无强制映射，尝试从 API 获取用户名...")
        
        # 优先从 user_page_data (GET_ALL模式)
        if user_page_data and len(user_page_data) > 0 and len(user_page_data[0]) > 2:
            base_name = user_page_data[0][-1].get('username')
        
        # 其次从 first_post_meta (ITERATIVE模式)
        if not base_name and first_post_meta:
            try:
                first_post_detail = first_post_meta[0][-1]
                base_name = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')
            except (IndexError, KeyError, TypeError):
                pass

        # 最后，如果都没有，再通过 post_urls 发起新请求
        if not base_name and post_urls:
            detailed_metadata = self.api.get_post_metadata(post_urls[0])
            if detailed_metadata:
                try:
                    first_post_detail = detailed_metadata[0][-1]
                    base_name = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')
                except (IndexError, KeyError, TypeError):
                    pass
        
        if base_name:
            print(f"  - [命名] 已通过 API 获取用户名: {base_name}")
            return self._format_folder_name(base_name, user_id)
        
        else:
            # --- 4. 获取失败的处理 (unknown 逻辑) ---
            print("  - [命名] 未能获取用户名。")
            # 最后的保底
            print(f"  - [命名] 将使用 'unknown_{user_id}' 作为文件夹名。")
            return f"unknown_{user_id}"