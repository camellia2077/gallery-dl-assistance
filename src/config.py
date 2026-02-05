# src/config.py

import os
import tomllib
from typing import Dict, Any, List

class Config:
    """
    应用程序配置类。
    支持 命令行 > 配置文件 > 报错 的优先级逻辑。
    """
    def __init__(self):
        # 1. 自动定位 config.toml 文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, 'config.toml')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件未找到: {config_path}")

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise RuntimeError(f"解析配置文件失败: {e}")

        # 2. 验证 TOML 中的静态字段 (那些不支持命令行的参数)
        # 对于支持命令行的参数，我们在加载时不强制要求存在
        self._validate_toml_basic(data)

        # 3. 映射配置
        # 【关键修改】使用 .get()，如果 TOML 里没有，就先设为 None
        self.RETRY_FAILED = data.get("retry_failed") 
        self.USERS_ID = data.get("users_id")
        
        # 静态参数直接读取
        self.DOWNLOAD_MODE = data["download_mode"]
        self.INCREMENTAL_DOWNLOAD = data["incremental_download"]
        self.COOKIE_FILE_PATH = data["cookie_file_path"]
        self.OUTPUT_DIR_PATH = data["output_dir_path"]
        self.USER_ID_TO_NAME_MAP = data.get("user_id_map", {})

    def _validate_toml_basic(self, data: Dict[str, Any]):
        """仅验证那些 CLI 无法覆盖的基础字段，或者字段存在时的类型检查。"""
        
        # 1. 检查绝对必须在 TOML 里存在的字段
        required_static_fields = [
            "download_mode", 
            "incremental_download", 
            "cookie_file_path", 
            "output_dir_path"
        ]
        # 注意：users_id 和 retry_failed 从必填列表中移除了
        
        for field in required_static_fields:
            if field not in data:
                raise ValueError(f"配置文件 config.toml 缺少基础必填字段: '{field}'")

        # 2. 类型检查 (如果字段存在的话)
        if "retry_failed" in data and not isinstance(data["retry_failed"], bool):
             raise TypeError(f"配置错误: 'retry_failed' 必须是 true 或 false")
        
        if "users_id" in data:
            if not isinstance(data["users_id"], list):
                raise TypeError(f"配置错误: 'users_id' 必须是列表")
            for uid in data["users_id"]:
                if not isinstance(uid, int):
                    raise TypeError(f"配置错误: 'users_id' 列表包含非整数项")

        # ... (其他静态字段的检查保持不变) ...
        if not isinstance(data["output_dir_path"], str):
             raise TypeError(f"配置错误: 'output_dir_path' 必须是字符串")

    def check_final_config(self):
        """
        【新增】最终校验方法。
        在 main.py 完成命令行参数覆盖后调用。
        如果此时关键参数仍为空，则报错。
        """
        # 校验 1: retry_failed
        # 如果 TOML 没填 (None)，且命令行也没传 (None)，则报错
        if self.RETRY_FAILED is None:
            raise ValueError(
                "配置缺失: 'retry_failed' (失败重试开关) 未设置。\n"
                "请在 config.toml 中设置 'retry_failed = true/false'，\n"
                "或使用命令行参数 '--retry / --no-retry'。"
            )

        # 校验 2: users_id
        # 如果 TOML 是空列表或没填，且命令行也没传 UID，则报错
        if not self.USERS_ID:
            raise ValueError(
                "配置缺失: 未指定要下载的用户 ID。\n"
                "请在 config.toml 的 'users_id' 中添加 ID，\n"
                "或使用命令行参数 '-u 123456'。"
            )