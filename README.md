# Bilibili 动态图片下载助手使用指南

本项目是一个基于 Python 的命令行工具，用于批量下载指定 Bilibili 用户的动态图片（包含原图、长图及实况照片 Live Photo），并自动保存相关的动态元数据。

下载结果如下，下载的时候也会获取动态的标题电子收藏量，以json格式存储。实况图片以mp4存储，同时也会保存图片格式。
<img width="1573" height="800" alt="image" src="https://github.com/user-attachments/assets/71ec030c-f096-4254-9c85-c00177338160" />


## 1. 环境准备

在使用本程序之前，请确保您的系统中已安装以下必要组件：

* **Python 3.11 或更高版本**：程序使用了 `tomllib` 库，该库在 Python 3.11 中引入。
* **gallery-dl**：核心依赖工具，用于解析 Bilibili 的数据。
* 安装命令：`pip install gallery-dl`


* **Cookie 文件（可选）**：如果需要下载仅限登录可见的内容或提高稳定性，建议准备 Netscape 格式的 Cookie 文件。

## 2. 配置说明

程序支持通过 `config.toml` 文件进行基础配置。请在项目根目录下创建该文件：

```toml
# config.toml 示例内容

# 下载模式：'GET_ALL' (一次性获取所有) 或 'ITERATIVE' (逐页获取，适合动态极多的用户)
download_mode = "ITERATIVE"

# 是否开启增量下载 (true: 跳过已下载的动态)
incremental_download = true

# Cookie 文件路径 (不使用可填空字符串)
cookie_file_path = "cookies.txt"

# 图片保存的根目录
output_dir_path = "./downloads"

# 默认下载的用户 ID 列表 (整数)
users_id = [123456, 789012]

# 是否重试之前下载失败的项目
retry_failed = true

# [可选] 用户名强制映射：UID = "自定义名称"
[user_id_map]
"123456" = "示例用户A"

```

## 3. 运行方式

### 3.1 基础运行

按照 `config.toml` 中的 `users_id` 列表顺序下载：

```bash
python src/main.py

```

### 3.2 命令行指定用户

使用 `-u` 参数指定用户 ID，这将忽略配置文件中的列表：

```bash
# 下载 UID 为 123456 的用户动态
python src/main.py -u 123456

# 下载 UID 为 123456 的用户并指定文件夹名称为 "MyFavorite"
python src/main.py -u 123456 -n MyFavorite

```

### 3.3 重试控制

您可以通过命令行强制覆盖配置文件中的重试设置：

* `--retry`: 强制开启失败重试。
* `--no-retry`: 强制关闭失败重试。

## 4. 输出结构

下载完成后，文件将按以下结构组织：

```text
downloads/
└── 用户名_UID/
    ├── 2024-01-01_动态ID.json        # 提取后的动态正文及统计数据
    ├── 2024-01-01_动态ID_1.jpg       # 图片资源
    ├── 2024-01-01_动态ID_1.mp4       # 实况照片对应的视频 (如有)
    ├── metadata/
    │   ├── step1/                    # 用户主页原始元数据
    │   └── step2/                    # 单条动态原始元数据
    └── undownloaded.json             # 记录下载失败的项目，供下次重试

```

## 5. 日志查看

* **运行日志**：保存在 `log/YYYY-MM/run_log_时间戳.log`，包含详细的下载进度和错误信息。
* **统计摘要**：保存在 `log/processing_time_log.json`，记录每个用户的处理耗时、下载数量等统计数据。

## 6. 注意事项

* **频率限制**：程序内置了随机冷却时间以降低被封禁风险。
* **文件夹命名优先级**：程序会优先使用命令行 `-n` 指定的名称，其次查找本地已有的 `Name_UID` 文件夹，最后尝试通过 API 获取用户名。

## 感谢与依赖 (Acknowledgements & Dependencies)

本项目依赖于强大的开源下载工具 **gallery-dl** 来实现主要的媒体内容获取功能。

### 核心依赖

| 工具 | 描述 | 链接 |
| :--- | :--- | :--- |
| **gallery-dl** | 一个命令行程序，用于从各种图库和图像主机下载图像，我们用它来下载 [Bilibili网站] 的媒体内容。 | [GitHub: gallery-dl](https://github.com/mikf/gallery-dl) |

### 许可声明

`gallery-dl` 是在 **[具体许可，例如：GPL-2.0-or-later]** 许可下发布的。本项目使用 `gallery-dl` 模块的行为受其许可条款约束。

