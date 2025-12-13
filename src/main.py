# src/main.py

from app import Application
from config import Config
from cli import parse_args, VERSION
from dependency import check_dependencies

def main():
    """
    主函数，作为程序的入口点。
    """
    # 1. 调用 cli.py 中的解析函数来处理命令行参数
    args = parse_args() 

    # 2. 环境依赖检查
    check_dependencies()

    # 3. ================= 开始下载的功能 =================
    
    print(f"正在启动 Bilibili Downloader v{VERSION} ...")
    
    # 创建配置对象
    app_config = Config()

    # 【新增】处理命令行覆盖参数
    cli_uid = args.get('uid')
    cli_name = args.get('name')

    if cli_uid:
        print(f"\n[CLI] 检测到命令行指定 UID: {cli_uid}")
        # 1. 覆盖要下载的用户列表
        app_config.USERS_ID = [cli_uid]
        
        # 2. 如果提供了自定义名称，注入到名称映射表中
        if cli_name:
            print(f"[CLI] 检测到命令行指定自定义名称: {cli_name}")
            # 确保 key 是字符串，因为 config.toml 解析出来的 map key 通常是字符串
            app_config.USER_ID_TO_NAME_MAP[str(cli_uid)] = cli_name
        else:
             print(f"[CLI] 未指定名称，将优先查找本地文件夹，其次自动获取 API 名称。")

    
    # 使用配置创建应用程序实例
    app = Application(app_config)
    
    # 运行应用程序
    app.run()

if __name__ == '__main__':
    main()