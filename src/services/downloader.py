# src/services/downloader.py

import os
import re
import datetime
import requests
import time
import json
from typing import List, Dict, Tuple, Literal

DownloadResult = Literal["SUCCESS", "SKIPPED", "FAILED"]

class Downloader:
    """负责下载图片文件，并管理失败的下载。"""

    def _get_undownloaded_filepath(self, folder: str) -> str:
        return os.path.join(folder, 'undownloaded.json')

    def retry_undownloaded(self, folder: str, user_name: str) -> Tuple[int, int, int, List[Dict]]:
        """
        尝试重新下载之前失败的图片。
        【修改】返回值增加一项，区分图片和视频: (成功图片数, 成功视频数, 失败数, 仍然未下载的列表)
        """
        undownloaded_path = self._get_undownloaded_filepath(folder)
        if not os.path.exists(undownloaded_path):
            return 0, 0, 0, []

        print(f"\n  - 检测到 'undownloaded.json'，正在尝试重新下载 {user_name} 的失败项目...")
        
        try:
            with open(undownloaded_path, 'r', encoding='utf-8') as f:
                failed_items = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  - 警告：读取 'undownloaded.json' 文件失败或格式错误，跳过重试: {e}")
            return 0, 0, 0, []

        still_failed = []
        successful_retries_img = 0
        successful_retries_vid = 0
        failed_retries = 0

        for item in failed_items:
            item['folder'] = folder
            
            result = self.download_image(**item)
            if result == "SUCCESS":
                # 【新增】通过URL后缀判断是图片还是视频
                url = item.get('url', '')
                if url.endswith('.mp4') or url.endswith('.mov'):
                    successful_retries_vid += 1
                else:
                    successful_retries_img += 1
            elif result == "FAILED":
                failed_retries += 1
                still_failed.append(item)
        
        print(f"  - 重试完成: {successful_retries_img + successful_retries_vid} 个成功 (图片:{successful_retries_img}/实况图片:{successful_retries_vid}), {failed_retries} 个失败。")
        return successful_retries_img, successful_retries_vid, failed_retries, still_failed

    def save_undownloaded_list(self, folder: str, undownloaded_items: List[Dict]):
        """将未下载的图片信息列表保存到 undownloaded.json 文件中。"""
        undownloaded_path = self._get_undownloaded_filepath(folder)
        
        unique_items = []
        seen_identifiers = set()
        
        for item in undownloaded_items:
            identifier = (item['url'], item['index'])
            if identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                item_to_save = item.copy()
                if 'folder' in item_to_save:
                    del item_to_save['folder']
                unique_items.append(item_to_save)

        if not unique_items:
            if os.path.exists(undownloaded_path):
                try:
                    os.remove(undownloaded_path)
                    print("\n  - 所有图片均已成功下载，已删除 'undownloaded.json'。")
                except OSError as e:
                    print(f"  - 警告：删除 'undownloaded.json' 文件失败: {e}")
            return

        print(f"\n  - 将 {len(unique_items)} 个未下载的项目信息保存到 'undownloaded.json'...")
        try:
            with open(undownloaded_path, 'w', encoding='utf-8') as f:
                json.dump(unique_items, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"  - 错误：写入 'undownloaded.json' 文件失败: {e}")


    def download_image(self, url: str, folder: str, pub_ts: int, id_str: str, index: int, user_name: str) -> DownloadResult:
            """
            下载单个图片文件，增加了重试机制和用户名显示。
            """
            try:
                date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
            except (ValueError, OSError):
                date_str = 'unknown_date'

            file_ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp|mp4|mov)', url, re.IGNORECASE)
            file_ext = file_ext_match.group(0) if file_ext_match else '.jpg'

            image_filename = f"{date_str}_{id_str}_{index}{file_ext}"
            filepath = os.path.join(folder, image_filename)

            if os.path.exists(filepath):
                return "SKIPPED"

            green_user_name = f"\033[92m{user_name}\033[0m"
            print(f"  -  正在下载用户 {green_user_name} 资源: {image_filename}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.bilibili.com/"
            }

            for attempt in range(3):
                try:
                    response = requests.get(url, stream=True, timeout=30, headers=headers)
                    response.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return "SUCCESS" 
                except requests.exceptions.RequestException as e:
                    status_code = e.response.status_code if e.response else "Unknown"
                    print(f"  - 下载失败 (状态码 {status_code}): {e}")
                    if attempt < 2:
                        print(f"  - 5秒后重试... (尝试 {attempt + 2}/3)")
                        time.sleep(6)
                    else:
                        print("  - 所有重试均失败，跳过此文件。")
            
            return "FAILED"