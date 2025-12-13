# src/config.py

import os
import tomllib
from typing import Dict, Any

class Config:
    """
    应用程序配置类。
    从项目根目录的 'config.toml' 文件中加载配置，并进行完整性验证。
    """
    def __init__(self):
        # 1. 自动定位 config.toml 文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, 'config.toml')

        # 2. 读取并解析 TOML 文件
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件未找到，请确保 'config.toml' 位于项目根目录: {config_path}")

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise RuntimeError(f"解析配置文件失败 (格式错误): {e}")

        # 3. 验证配置数据的合法性
        self._validate_config(data)

        # 4. 将 TOML 配置映射到类属性
        self.DOWNLOAD_MODE = data["download_mode"]
        self.USERS_ID = data["users_id"]
        self.INCREMENTAL_DOWNLOAD = data["incremental_download"]
        self.COOKIE_FILE_PATH = data["cookie_file_path"]
        self.OUTPUT_DIR_PATH = data["output_dir_path"]
        self.USER_ID_TO_NAME_MAP = data.get("user_id_map", {})

    def _validate_config(self, data: Dict[str, Any]):
        """
        验证配置字典的合法性。
        检查必填字段、数据类型和有效值范围。
        """
        # --- 1. 检查必填字段是否存在 ---
        required_fields = [
            "download_mode", 
            "users_id", 
            "incremental_download", 
            "cookie_file_path", 
            "output_dir_path"
        ]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"配置文件 config.toml 缺少必填字段: '{field}'")

        # --- 2. 检查数据类型 ---
        
        # download_mode 必须是字符串
        if not isinstance(data["download_mode"], str):
            raise TypeError(f"配置错误: 'download_mode' 必须是字符串，实际为 {type(data['download_mode']).__name__}")

        # users_id 必须是列表
        if not isinstance(data["users_id"], list):
            raise TypeError(f"配置错误: 'users_id' 必须是列表 (例如 [123, 456])，实际为 {type(data['users_id']).__name__}")

        # users_id 中的每一项必须是整数
        for uid in data["users_id"]:
            if not isinstance(uid, int):
                raise TypeError(f"配置错误: 'users_id' 列表包含非整数项: {uid} ({type(uid).__name__})")

        # incremental_download 必须是布尔值
        if not isinstance(data["incremental_download"], bool):
            raise TypeError(f"配置错误: 'incremental_download' 必须是 true 或 false")

        # 路径必须是字符串
        if not isinstance(data["cookie_file_path"], str):
            raise TypeError(f"配置错误: 'cookie_file_path' 必须是字符串")
        if not isinstance(data["output_dir_path"], str):
            raise TypeError(f"配置错误: 'output_dir_path' 必须是字符串")

        # user_id_map (如果存在) 必须是字典
        if "user_id_map" in data and not isinstance(data["user_id_map"], dict):
            raise TypeError(f"配置错误: 'user_id_map' 必须是键值对映射 (Table)")

        # --- 3. 检查值的有效性 ---

        # 验证 download_mode 的值
        valid_modes = ["ITERATIVE", "GET_ALL"]
        if data["download_mode"] not in valid_modes:
            raise ValueError(f"配置错误: 'download_mode' 的值无效。必须是 {valid_modes} 中的一个，实际为: '{data['download_mode']}'")

        # 验证路径非空
        if not data["cookie_file_path"].strip():
            print("警告: 'cookie_file_path' 为空，可能导致需要登录的内容无法下载。")
        
        if not data["output_dir_path"].strip():
            raise ValueError("配置错误: 'output_dir_path' (输出目录) 不能为空。")

        # 验证 users_id 列表非空 (可选，视需求而定，这里仅给警告)
        if not data["users_id"]:
            print("警告: 'users_id' 列表为空，程序运行后将不会下载任何内容。")