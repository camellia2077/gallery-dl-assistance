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

    def process(self, user_name: str, post_url: str, user_folder: str) -> Tuple[bool, int, int, List[Dict]]:
        """
        处理单个动态，协调提取、保存和下载任务。
        【修改】返回元组扩展为: (是否继续, 成功图片数, 成功视频数, 失败列表)
        技术实现说明:
        B站实况视频(Live Photo)的数据结构如下：
        - 'url': 对应静态图片 (JPG)
        - 'live_url': 对应实况视频 (MP4) - 该字段仅在存在实况时出现
        
        本方法会同时检查这两个字段：
        1. 总是下载 'url' 对应的图片。
        2. 如果检测到 'live_url'，则额外下载对应的 MP4 文件，文件名与图片保持一致（扩展名不同）。
        """
        images_data = self.api.get_post_metadata(post_url)
        # 注意：这里返回4个值
        if not images_data or not isinstance(images_data[0][-1], dict):
            print(f"  - 警告：未找到动态 {post_url} 的有效数据，跳过。")
            return True, 0, 0, []

        if images_data and len(images_data) > 0 and isinstance(images_data[0], list):
             if isinstance(images_data[0][-1], dict):
                 images_data[0][-1]['url'] = post_url

        first_image_meta = images_data[0][-1]
        id_str = first_image_meta.get('detail', {}).get('id_str')
        pub_ts = first_image_meta.get('detail', {}).get('modules', {}).get('module_author', {}).get('pub_ts')

        if not (id_str and pub_ts):
            print(f"  - 警告：无法从元数据中获取动态 ID 或发布时间戳，跳过。")
            return True, 0, 0, []

        try:
            date_str = datetime.datetime.fromtimestamp(pub_ts).strftime('%Y-%m-%d')
        except (ValueError, OSError):
            date_str = 'unknown_date'
        
        content_json_filename = f"{date_str}_{id_str}.json"
        content_json_filepath = os.path.join(user_folder, content_json_filename)
        
        # 增量下载检查逻辑
        if self.config.INCREMENTAL_DOWNLOAD and os.path.exists(content_json_filepath):
            has_missing_live_photo = False
            for idx, img_info in enumerate(images_data[1:]):
                if isinstance(img_info, list) and len(img_info) > 0 and isinstance(img_info[-1], dict):
                    meta = img_info[-1]
                    if meta.get('live_url'):
                        video_filename = f"{date_str}_{id_str}_{idx+1}.mp4"
                        video_path = os.path.join(user_folder, video_filename)
                        if not os.path.exists(video_path):
                            has_missing_live_photo = True
                            print(f"  - [增量检查] 动态 {id_str} 发现缺失的实况视频，将进行补充下载。")
                            break
            
            if not has_missing_live_photo:
                # 均已存在，返回 0, 0
                return False, 0, 0, []

        self.saver.save_step2_metadata(images_data, user_folder, date_str, pub_ts, id_str)

        successful_images = 0
        successful_videos = 0
        failed_downloads_info: List[Dict] = []
        total_items_to_process = 0
        skipped_count = 0

        # 遍历每一个图片项进行下载处理
        for index, image_info in enumerate(images_data[1:]):
            if not isinstance(image_info, list) or not isinstance(image_info[-1], dict):
                continue
                
            meta_dict = image_info[-1]
            total_items_to_process += 1

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
                    successful_images += 1
                elif result == "FAILED":
                    failed_downloads_info.append(download_args)
                elif result == "SKIPPED":
                    skipped_count += 1
            
            # ----------------- 2. 下载实况视频 (Live Photo) -----------------
            live_photo_url = meta_dict.get('live_url')
            if live_photo_url:
                # 实况视频作为一个额外项目，不算在基础skipped_count的total里，除非我们想更精细
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
                        successful_videos += 1
                    elif v_result == "FAILED":
                        failed_downloads_info.append(video_args)
        
        if skipped_count > 0 and skipped_count >= total_items_to_process:
             # 注意：这里只打印了图片的跳过信息，视频通常伴随图片存在
            print(f"  - 所有 {skipped_count} 张图片均已存在，全部跳过。")
        elif skipped_count > 0:
            print(f"  - 跳过 {skipped_count} 张已存在的图片。")

        self.extractor.create_content_json_from_local_meta(user_folder, date_str, id_str)

        # 返回图片和视频的独立计数
        return True, successful_images, successful_videos, failed_downloads_info