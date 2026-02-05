# src/processor/processor.py

from api import BilibiliAPI
from config import Config
from services.content_extractor import ContentExtractor
from services.downloader import Downloader
from services.folder_resolver import FolderNameResolver
from services.metadata_saver import MetadataSaver
from .post_handler import PostHandler
from .user_processor import UserProcessor

class PostProcessorFacade:
    """
    外观模式 (Facade Pattern)
    负责初始化所有必要的服务和处理器，并将它们组装在一起。
    对外提供统一的 process_user 接口。
    """

    def __init__(self, base_output_dir: str, api: BilibiliAPI, config: Config):
        # 1. 初始化基础服务
        self.resolver = FolderNameResolver(base_output_dir, api, config)
        self.saver = MetadataSaver()
        self.downloader = Downloader()
        self.extractor = ContentExtractor()

        # 2. 初始化核心处理器
        # PostHandler 负责处理单个动态
        self.post_handler = PostHandler(api, config, self.extractor, self.downloader, self.saver)
        
        # UserProcessor 负责处理用户级逻辑 (遍历动态列表)
        self.user_processor = UserProcessor(api, config, self.resolver, self.saver, self.post_handler)

    def process_user(self, user_id: int, user_url: str) -> dict:
        """
        处理单个用户的所有流程。
        直接委托给 UserProcessor 执行。
        """
        return self.user_processor.process(user_id, user_url)