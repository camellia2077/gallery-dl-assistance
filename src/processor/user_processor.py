# src/processor/user_processor.py

import os
import time
import random 

from typing import Dict, List, Iterable
from tqdm import tqdm
from api import BilibiliAPI
from config import Config
from services.folder_resolver import FolderNameResolver
from services.metadata_saver import MetadataSaver
from .post_handler import PostHandler

class UserProcessor:
    """处理单个用户的完整流程。"""

    def __init__(self, api: BilibiliAPI, config: Config, resolver: FolderNameResolver, saver: MetadataSaver, handler: PostHandler):
        self.api = api
        self.config = config
        self.resolver = resolver
        self.saver = saver
        self.handler = handler

    def process(self, user_id: int, user_url: str) -> Dict:
        """
        处理单个用户的主逻辑。
        """
        print(f"\n>>>>>>>>> 开始处理用户ID: {user_id} ({user_url}) <<<<<<<<<")

        post_urls_iterable: Iterable[str]
        total_posts = 0

        if self.config.DOWNLOAD_MODE == 'ITERATIVE':
            print("\n[步骤1] 使用 'ITERATIVE' 模式，正在准备迭代获取动态 URL...")
            post_urls_iterable = self.api.get_post_urls_iterative(user_id)
        else:
            print("\n[步骤1] 使用 'GET_ALL' 模式，正在一次性获取所有动态 URL...")
            user_page_data = self.api.get_initial_metadata(user_url)

            if not user_page_data:
                print("  - 未收到任何数据，跳过此用户。")
                return {"processed_posts": 0, "downloaded_images": 0, "downloaded_videos": 0, "failed_images": 0, "folder_name": str(user_id)}

            post_urls = [item[1] for item in user_page_data if len(item) > 1]
            total_posts = len(post_urls)
            print(f"找到了 {total_posts} 条动态。")
            post_urls_iterable = post_urls
            
            folder_name = self.resolver.determine_folder_name(user_id, user_page_data, post_urls)
            user_folder = os.path.join(self.resolver.base_output_dir, folder_name)
            os.makedirs(user_folder, exist_ok=True)
            
            print(f"用户识别为: '{folder_name}'")
            print(f"文件将保存至: {user_folder}")

            self.saver.save_step1_metadata(user_url, user_folder, user_page_data)

        folder_name = ""
        user_folder = ""
        is_first_post = True

        # 重试失败项目
        temp_folder_name = self.resolver.determine_folder_name_pre_scan(user_id)
        if temp_folder_name:
            user_folder = os.path.join(self.resolver.base_output_dir, temp_folder_name)
            # 【修改】接收新的返回值: (img_count, vid_count, failed, still_failed_list)
            successful_retry_imgs, successful_retry_vids, _, persistent_failures = self.handler.downloader.retry_undownloaded(user_folder, temp_folder_name)
        else:
            successful_retry_imgs, successful_retry_vids, persistent_failures = 0, 0, []

        print(f"\n[步骤2] 开始处理用户 {user_id} 的动态...")
        
        processed_posts_count = 0
        total_successful_images = successful_retry_imgs
        total_successful_videos = successful_retry_vids # 【新增】
        session_failures: List[Dict] = []
        
        for url in tqdm(post_urls_iterable, desc="处理动态", unit=" 条", total=total_posts if total_posts > 0 else None):
            time.sleep(random.uniform(1.5, 3.5))
            if is_first_post:
                if not temp_folder_name:
                    first_post_meta = self.api.get_post_metadata(url)
                    folder_name = self.resolver.determine_folder_name(user_id, None, [url], first_post_meta)
                else:
                    folder_name = temp_folder_name

                user_folder = os.path.join(self.resolver.base_output_dir, folder_name)
                os.makedirs(user_folder, exist_ok=True)
                if is_first_post and not temp_folder_name: # 只打印一次
                    print(f"\n用户识别为: '{folder_name}'")
                    print(f"文件将保存至: {user_folder}")
                is_first_post = False
            
            # 【修改】接收拆分后的统计数据
            should_continue, s_imgs, s_vids, new_failures = self.handler.process(folder_name, url, user_folder)
            
            if not should_continue:
                green_user_name_plain = f"'{folder_name}'"
                print(f"\n  - 增量下载模式：检测到已下载的内容，将停止处理用户 {green_user_name_plain} 的剩余动态。")
                break
            
            processed_posts_count += 1
            total_successful_images += s_imgs
            total_successful_videos += s_vids # 【新增】
            if new_failures:
                session_failures.extend(new_failures)
        
        if not user_folder and temp_folder_name:
             user_folder = os.path.join(self.resolver.base_output_dir, temp_folder_name)

        if user_folder:
            all_failures = persistent_failures + session_failures
            self.handler.downloader.save_undownloaded_list(user_folder, all_failures)
            total_failed_downloads = len(all_failures)
        else:
            total_failed_downloads = 0

        # 【修改】返回结果字典包含 videos
        return {
            "processed_posts": processed_posts_count,
            "downloaded_images": total_successful_images,
            "downloaded_videos": total_successful_videos,
            "failed_images": total_failed_downloads,
            "folder_name": folder_name if folder_name else str(user_id)
        }