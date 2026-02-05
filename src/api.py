# src/api.py

import random
import time
import subprocess
import json
import requests
import http.cookiejar
from typing import List, Dict, Any, Optional, Iterator

class BilibiliAPI:
    """一个用于通过 gallery-dl 或直接API与 Bilibili 交互的封装器。"""
    
    def __init__(self, cookie_file: Optional[str]):
        """初始化 API 封装器。"""
        self.cookie_file = cookie_file
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        })
        if self.cookie_file:
            self._load_cookies()

    def _load_cookies(self):
        """从 Netscape 格式的 cookie 文件加载 cookie 到 session 中。"""
        try:
            jar = http.cookiejar.MozillaCookieJar(self.cookie_file)
            jar.load()
            self.session.cookies.update(jar)
        except Exception as e:
            print(f"  - 警告：加载 cookie 文件失败: {e}")

    def _run_command(self, url: str) -> Optional[List[Dict[str, Any]]]:
            """通过 gallery-dl 运行命令并解析其 JSON 输出。"""
            command = ['gallery-dl', '-j', url]
            if self.cookie_file:
                command.extend(['--cookies', self.cookie_file])
            # 防止解析的时候卡住
            # 最大重试次数设置为 2 次（初始 1 次 + 重试 1 次）
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    # 【修改点】设置 timeout=30，单位为秒
                    result = subprocess.run(command, check=True, capture_output=True, timeout=30)
                    try:
                        output_text = result.stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        output_text = result.stdout.decode('gbk', errors='ignore')
                    return json.loads(output_text)

                except subprocess.TimeoutExpired:
                    print(f"  - 错误: 获取元数据超时 (30s) [尝试 {attempt + 1}/{max_retries}]")
                except (subprocess.CalledProcessError, json.JSONDecodeError, Exception) as e:
                    print(f"  - 错误: gallery-dl 执行或解析失败 [尝试 {attempt + 1}/{max_retries}]: {e}")
                
                # 如果不是最后一次尝试，则打印重试提示
                if attempt < max_retries - 1:
                    print(f"  - 正在重试...")
                else:
                    print(f"  - 所有重试均失败，跳过 URL: {url}")

            return None
    
    def get_post_metadata(self, post_url: str) -> Optional[List[Dict[str, Any]]]:
        """获取单个动态的详细元数据。"""
        return self._run_command(post_url)

    def get_initial_metadata(self, user_url: str) -> Optional[List[Dict[str, Any]]]:
        """【GET_ALL模式】获取用户所有动态的元数据。"""
        return self._run_command(user_url)

    def get_post_urls_iterative(self, user_id: int) -> Iterator[str]:
        """
        【ITERATIVE模式】
        通过直接请求B站API，逐页获取并实时产出(yield)单个动态的URL。
        这是一个生成器，实现了边获取边处理。
        """
        api_url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/opus/feed/space"
        params = {"host_mid": str(user_id), "offset": ""}

        sleep_time = random.uniform(2.0, 4.0)
        # 仅在不是第一次请求时打印休息信息，避免刷屏（可选）
        if params["offset"]: 
            # print(f"  - (防反爬) 翻页冷却中，休息 {sleep_time:.2f} 秒...")
                pass 
        time.sleep(sleep_time)
        
        while True:
            try:
                response = self.session.get(api_url, params=params, timeout=20)
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 0:
                    print(f"  - API错误: {data.get('message', '未知错误')}")
                    break
                
                items = data.get("data", {}).get("items", [])
                if not items:
                    break

                for item in items:
                    if item.get("opus_id"):
                        yield f"https://www.bilibili.com/opus/{item['opus_id']}"
                
                if not data.get("data", {}).get("has_more"):
                    break
                
                # 【修改点】更新 offset 以便进行翻页
                # 使用 'opus_id' 而不是 'opus_id_str'
                params["offset"] = items[-1].get("opus_id", "")
                if not params["offset"]:
                    print("  - 错误：无法获取下一页的 offset，停止获取。")
                    break

            except requests.exceptions.RequestException as e:
                print(f"  - 网络错误: {e}")
                break
            except json.JSONDecodeError:
                print(f"  - API响应解析失败。")
                break