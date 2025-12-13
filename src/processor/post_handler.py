# src/processor/post_handler.py

import os
import datetime
from typing import Tuple, List, Dict
from api import BilibiliAPI
from config import Config

from services.content_extractor import ContentExtractor
from services.downloader import Downloader
from services.metadata_saver import MetadataSaver

class PostHandler:
    """处理单个动态的完整流程。"""

    def __init__(self, api: BilibiliAPI, config: Config, extractor: ContentExtractor, downloader: Downloader, saver: MetadataSaver):
        self.api = api
        self.config = config
        self.extractor = extractor
        self.downloader = downloader
        self.saver = saver

    def process(self, user_name: str, post_url: str, user_folder: str) -> Tuple[bool, int, List[Dict]]:
        """
        处理单个动态，协调提取、保存和下载任务。
        返回一个元组: (是否继续处理下一个动态, 成功下载的图片数, 失败下载的图片信息列表)
        """
        images_data = self.api.get_post_metadata(post_url)
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return True, 0, []

        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        if not (id_str and pub_ts):
            print(f"  - 警告：无法从元数据中获取动态 ID 或发布时间戳，跳过。")
            return True, 0, []

        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'
        
        content_json_filename = f"{date_str}_{id_str}.json"
        content_json_filepath = os.path.join(user_folder, content_json_filename)
        
        # ------------------ 修改后的增量检查逻辑 ------------------
        # 如果开启了增量下载，且内容信息文件已存在
        if self.config.INCREMENTAL_DOWNLOAD and os.path.exists(content_json_filepath):
            # 即使 JSON 存在，也要检查一下是否有可能缺失的 Live Photo (实况视频)
            has_missing_live_photo = False
            
            for idx, img_info in enumerate(images_data[1:]):
                if isinstance(img_info, list) and len(img_info) > 0 and isinstance(img_info[-1], dict):
                    meta = img_info[-1]
                    if meta.get('live_url'):
                        # 构建预期的视频文件名 (命名规则需与下载逻辑保持一致)
                        video_filename = f"{date_str}_{id_str}_{idx+1}.mp4"
                        video_path = os.path.join(user_folder, video_filename)
                        
                        if not os.path.exists(video_path):
                            has_missing_live_photo = True
                            print(f"  - [增量检查] 动态 {id_str} 发现缺失的实况视频，将进行补充下载。")
                            break
            
            if not has_missing_live_photo:
                return False, 0, []
        # -------------------------------------------------------

        # 在保存前检查步骤2的元数据文件是否存在
        metadata_filename = f"{date_str}_{id_str}.json"
        metadata_filepath = os.path.join(user_folder, 'metadata', 'step2', metadata_filename)
        if not os.path.exists(metadata_filepath):
            self.saver.save_step2_metadata(images_data, user_folder, date_str, pub_ts, id_str)
        else:
            print(f"  - 步骤2元数据 '{metadata_filename}' 已存在，跳过保存。")
        
        successful_downloads = 0
        failed_downloads_info: List[Dict] = []
        total_images_to_process = len(images_data) - 1
        skipped_count = 0

        # 遍历每一个图片项进行下载处理
        for index, image_info in enumerate(images_data[1:]):
            if not isinstance(image_info, list) or not isinstance(image_info[-1], dict):
                continue
                
            meta_dict = image_info[-1]

            # ----------------- 1. 下载图片 -----------------
            if meta_dict.get('url'):
                image_url = meta_dict['url']
                download_args = {
                    "url": image_url,
                    "folder": user_folder,
                    "pub_ts": pub_ts,
                    "id_str": id_str,
                    "index": index + 1,
                    "user_name": user_name
                }
                
                result = self.downloader.download_image(**download_args)
                if result == "SUCCESS":
                    successful_downloads += 1
                elif result == "FAILED":
                    failed_downloads_info.append(download_args)
                elif result == "SKIPPED":
                    skipped_count += 1
            
            # ----------------- 2. 下载实况视频 (Live Photo) -----------------
            # 使用上面定义好的 meta_dict 来获取 live_url
            live_photo_url = meta_dict.get('live_url')
            if live_photo_url:
                # 【核心修改点】
                # 先构建文件名，检查文件是否存在。
                # 只有文件不存在时，才打印日志并调用下载器。
                video_filename = f"{date_str}_{id_str}_{index + 1}.mp4"
                video_filepath = os.path.join(user_folder, video_filename)

                if not os.path.exists(video_filepath):
                    print(f"  - [Live Photo] 发现实况视频 (P{index + 1})，正在下载...")
                    
                    video_args = {
                        "url": live_photo_url,
                        "folder": user_folder,
                        "pub_ts": pub_ts,
                        "id_str": id_str,
                        "index": index + 1,
                        "user_name": user_name
                    }
                    
                    v_result = self.downloader.download_image(**video_args)
                    if v_result == "SUCCESS":
                        successful_downloads += 1
                    elif v_result == "FAILED":
                        failed_downloads_info.append(video_args)
                # else: 
                #   如果文件已存在，这里什么都不做（静默跳过），这样就不会打印那行误导人的日志了。
        
        if skipped_count > 0 and skipped_count == total_images_to_process:
            print(f"  - 所有 {skipped_count} 张图片均已存在，全部跳过。")
        elif skipped_count > 0:
            print(f"  - 跳过 {skipped_count} 张已存在的图片。")

        self.extractor.create_content_json_from_local_meta(user_folder, date_str, id_str)

        return True, successful_downloads, failed_downloads_info