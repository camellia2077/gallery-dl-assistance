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
        self.config = config  # 保存config实例
        self.resolver = resolver
        self.saver = saver
        self.handler = handler

    def process(self, user_id: int, user_url: str) -> Dict:
        """
        处理单个用户的主逻辑。
        根据 config 中的 DOWNLOAD_MODE 选择不同的获取策略。
        """
        print(f"\n>>>>>>>>> 开始处理用户ID: {user_id} ({user_url}) <<<<<<<<<")

        post_urls_iterable: Iterable[str]
        total_posts = 0

        # 【核心修改】根据配置选择不同的模式
        if self.config.DOWNLOAD_MODE == 'ITERATIVE':
            print("\n[步骤1] 使用 'ITERATIVE' 模式，正在准备迭代获取动态 URL...")
            post_urls_iterable = self.api.get_post_urls_iterative(user_id)
            # 在迭代模式下，我们无法预先知道总数，tqdm 会自动处理这种情况
        else: # 默认为 'GET_ALL' 模式
            print("\n[步骤1] 使用 'GET_ALL' 模式，正在一次性获取所有动态 URL...")
            user_page_data = self.api.get_initial_metadata(user_url)

            if not user_page_data:
                print("  - 未收到任何数据，跳过此用户。")
                return {"processed_posts": 0, "downloaded_images": 0, "failed_images": 0, "folder_name": str(user_id)}

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

        # 在 'ITERATIVE' 模式下，我们必须在处理第一条动态时才能确定文件夹名称
        folder_name = ""
        user_folder = ""
        is_first_post = True

        # 在处理新动态之前，重试之前失败的下载 (这需要提前知道文件夹)
        # 为了兼容两种模式，我们先尝试确定文件夹
        temp_folder_name = self.resolver.determine_folder_name_pre_scan(user_id)
        if temp_folder_name:
            user_folder = os.path.join(self.resolver.base_output_dir, temp_folder_name)
            successful_retries, _, persistent_failures = self.handler.downloader.retry_undownloaded(user_folder, temp_folder_name)
        else:
            successful_retries, persistent_failures = 0, []

        print(f"\n[步骤2] 开始处理用户 {user_id} 的动态...")
        
        processed_posts_count = 0
        total_successful_downloads = successful_retries
        session_failures: List[Dict] = []
        
        # tqdm 可以完美处理列表和生成器
        for url in tqdm(post_urls_iterable, desc="处理动态", unit=" 条", total=total_posts if total_posts > 0 else None):
            # 【新增】在处理每条动态前，随机休息 1.5 ~ 3.5 秒
            time.sleep(random.uniform(1.5, 3.5))
            if is_first_post:
                # 在处理第一条动态时，获取其详细信息以确定用户名和文件夹
                # 这部分逻辑在 post_handler.process 内部完成，但我们需要先创建文件夹
                if not temp_folder_name:
                    # 如果预扫描失败，则需要用第一条动态来确定
                    # 为了简化，我们假设 post_handler 能处理文件夹不存在的情况，
                    # 或者在 handler 内部创建它。
                    # 目前的逻辑是，handler接收user_folder, 所以必须提前创建。
                    # 我们用第一条URL来获取信息并创建文件夹。
                    first_post_meta = self.api.get_post_metadata(url)
                    folder_name = self.resolver.determine_folder_name(user_id, None, [url], first_post_meta)
                else:
                    folder_name = temp_folder_name

                user_folder = os.path.join(self.resolver.base_output_dir, folder_name)
                os.makedirs(user_folder, exist_ok=True)
                print(f"\n用户识别为: '{folder_name}'")
                print(f"文件将保存至: {user_folder}")
                is_first_post = False
            
            should_continue, successful, new_failures = self.handler.process(folder_name, url, user_folder)
            
            if not should_continue:
                green_user_name_plain = f"'{folder_name}'"
                print(f"\n  - 增量下载模式：检测到已下载的内容，将停止处理用户 {green_user_name_plain} 的剩余动态。")
                break
            
            processed_posts_count += 1
            total_successful_downloads += successful
            if new_failures:
                session_failures.extend(new_failures)
        
        # 确保即使没有处理任何帖子，文件夹也已创建
        if not user_folder and temp_folder_name:
             user_folder = os.path.join(self.resolver.base_output_dir, temp_folder_name)

        if user_folder:
            all_failures = persistent_failures + session_failures
            self.handler.downloader.save_undownloaded_list(user_folder, all_failures)
            total_failed_downloads = len(all_failures)
        else:
            # 如果从未创建文件夹（例如，用户没有任何动态），则失败数为0
            total_failed_downloads = 0


        return {
            "processed_posts": processed_posts_count,
            "downloaded_images": total_successful_downloads,
            "failed_images": total_failed_downloads,
            "folder_name": folder_name if folder_name else str(user_id)
        }