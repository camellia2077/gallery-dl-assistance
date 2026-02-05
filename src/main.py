# src/main.py

import sys
from app import Application
from config import Config
from cli import parse_args, VERSION
from dependency import check_dependencies

def main():
    """
    主函数，作为程序的入口点。
    """
    # 1. 解析命令行参数
    args = parse_args() 

    # 2. 环境依赖检查
    check_dependencies()

    print(f"正在启动 Bilibili Downloader v{VERSION} ...")
    
    try:
        # 创建配置对象 (加载 config.toml)
        app_config = Config()

        # ==================== 1. 处理 retry_failed ====================
        cli_retry_failed = args.get('retry_failed')
        
        if cli_retry_failed is not None:
            # 命令行存在 -> 覆盖
            state_str = "开启" if cli_retry_failed else "关闭"
            print(f"[CLI] 检测到参数 --retry/--no-retry，强制{state_str}失败重试功能。")
            app_config.RETRY_FAILED = cli_retry_failed
        else:
            # 命令行缺失 -> 提示使用配置文件
            config_state = "开启" if app_config.RETRY_FAILED else "关闭"
            print(f"[CLI] 未检测到重试参数，将使用配置文件默认设置: {config_state}")

        # ==================== 2. 处理 uid (用户ID) ====================
        cli_uid = args.get('uid')
        cli_name = args.get('name')

        if cli_uid:
            # 命令行存在 -> 覆盖
            print(f"\n[CLI] 检测到命令行指定 UID: {cli_uid}")
            app_config.USERS_ID = [cli_uid]
            
            if cli_name:
                print(f"[CLI] 检测到命令行指定自定义名称: {cli_name}")
                app_config.USER_ID_TO_NAME_MAP[str(cli_uid)] = cli_name
            else:
                 print(f"[CLI] 未指定名称，将优先查找本地文件夹，其次自动获取 API 名称。")
        else:
            # 命令行缺失 -> 提示使用配置文件
            count = len(app_config.USERS_ID) if app_config.USERS_ID else 0
            print(f"[CLI] 未检测到 UID 参数，将处理配置文件列表中的 {count} 个用户。")

        # ==================== 3. 最终校验 (配合上一轮的 Config 修改) ====================
        # 如果 Config 类中实现了 check_final_config 方法，可以在这里调用
        if hasattr(app_config, 'check_final_config'):
            app_config.check_final_config()
        elif not app_config.USERS_ID:
            # 保底的手动检查
            print("\n" + "!"*50)
            print(" [错误] 未指定要下载的用户！请在 config.toml 中配置或使用 -u 参数。")
            print("!"*50 + "\n")
            sys.exit(1)

    except (ValueError, TypeError, RuntimeError) as e:
        print("\n" + "!"*50)
        print(f" [启动配置错误] {e}")
        print("!"*50 + "\n")
        sys.exit(1)

    # 运行应用程序
    app = Application(app_config)
    app.run()

if __name__ == '__main__':
    main()