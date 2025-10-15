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
        return re.sub(r'[\\/*?:"<>|]', "", filename).strip()

    def _scan_for_existing_folder(self, user_id: int) -> Optional[str]:
        """扫描输出目录，通过元数据反向查找与user_id匹配的文件夹名。"""
        print("  - 警告：正在扫描现有文件夹以匹配用户ID... 这可能需要一些时间。")
        try:
            # 确保基础目录存在，避免在扫描时出错
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
                        # 健壮性检查，确保数据结构符合预期
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
        """
        一个轻量级的方法，仅通过Config映射和本地扫描来尝试确定文件夹名，
        不进行任何API调用。用于在迭代模式下提前确定文件夹以重试下载。
        """
        user_id_str = str(user_id)
        if user_id_str in self.config.USER_ID_TO_NAME_MAP:
            mapped_name = self.config.USER_ID_TO_NAME_MAP[user_id_str]
            # 这里不需要打印，因为这个方法应该尽可能“安静”
            return self._sanitize_filename(mapped_name)

        # 仅当无法从Config映射中找到时才扫描
        return self._scan_for_existing_folder(user_id)

    def determine_folder_name(self, user_id: int, user_page_data: Optional[List[Dict]], post_urls: List[str], first_post_meta: Optional[List[Dict]] = None) -> str:
        """
        通过多级回退机制确定文件夹名称。
        最高优先级: Config映射 -> API获取 -> 扫描本地文件夹 -> 数字ID
        """
        user_id_str = str(user_id)
        if user_id_str in self.config.USER_ID_TO_NAME_MAP:
            mapped_name = self.config.USER_ID_TO_NAME_MAP[user_id_str]
            print(f"  - 在Config文件中找到高优先级映射: {user_id_str} -> {mapped_name}")
            return self._sanitize_filename(mapped_name)

        print("  - Config文件中无映射，尝试从API获取用户名...")
        username = None
        
        # 优先从 user_page_data (GET_ALL模式)
        if user_page_data and len(user_page_data) > 0 and len(user_page_data[0]) > 2:
            username = user_page_data[0][-1].get('username')
        
        # 其次从 first_post_meta (ITERATIVE模式)
        if not username and first_post_meta:
            try:
                first_post_detail = first_post_meta[0][-1]
                username = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')
            except (IndexError, KeyError, TypeError):
                pass # 静默处理错误，允许继续回退

        # 最后，如果都没有，再通过 post_urls 发起新请求
        if not username and post_urls:
            detailed_metadata = self.api.get_post_metadata(post_urls[0])
            if detailed_metadata:
                try:
                    first_post_detail = detailed_metadata[0][-1]
                    username = first_post_detail.get('username') or first_post_detail.get('detail', {}).get('modules', {}).get('module_author', {}).get('name')
                except (IndexError, KeyError, TypeError):
                    pass

        if username:
            print(f"  - 已通过API获取用户名: {username}")
            return self._sanitize_filename(username)

        print("  - 未能从API获取用户名，将尝试扫描本地文件夹...")
        folder_name = self._scan_for_existing_folder(user_id)
        if folder_name:
            return folder_name

        print(f"  - 未找到任何匹配项，将使用数字ID '{user_id}' 作为文件夹名。")
        return str(user_id)