#!/usr/bin/env python3
"""
Telegram机器人设置脚本
-------------------
安装Telegram机器人所需依赖并设置环境变量
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 将项目根目录添加到路径
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root.parent))

# 尝试导入配置模块
try:
    from audioprocess.config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS
except ImportError:
    print("无法导入配置模块，请确保项目路径正确")
    sys.exit(1)

def install_dependencies():
    """安装Telegram机器人所需的依赖包"""
    print("安装Telegram机器人所需依赖...")
    
    # 定义依赖包
    dependencies = [
        "python-telegram-bot==13.15",  # 使用13.x版本适配异步代码
    ]
    
    try:
        # 使用pip安装依赖
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + dependencies)
        print("依赖安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖失败: {e}")
        return False

def configure_telegram_bot():
    """配置Telegram机器人环境变量"""
    print("\n配置Telegram机器人...")
    
    # 检查是否已设置BOT TOKEN
    current_token = TELEGRAM_BOT_TOKEN
    if current_token:
        print(f"当前Bot Token: {current_token[:5]}...{current_token[-5:]}")
        change = input("是否需要修改Bot Token? (y/N): ").strip().lower()
        if change != 'y':
            print("保持当前Bot Token不变")
        else:
            new_token = input("请输入新的Bot Token: ").strip()
            if new_token:
                # 更新配置文件中的TOKEN
                update_config_value("TELEGRAM_BOT_TOKEN", new_token)
                print("Bot Token已更新")
    else:
        new_token = input("请输入Telegram Bot Token: ").strip()
        if new_token:
            # 更新配置文件中的TOKEN
            update_config_value("TELEGRAM_BOT_TOKEN", new_token)
            print("Bot Token已设置")
        else:
            print("警告: 未设置Bot Token，机器人将无法启动")
    
    # 检查允许的用户
    current_users = TELEGRAM_ALLOWED_USERS
    if current_users and current_users[0]:  # 检查列表非空且第一项非空字符串
        users_str = ", ".join(current_users)
        print(f"当前允许的用户ID: {users_str}")
        change = input("是否需要修改允许的用户ID列表? (y/N): ").strip().lower()
        if change != 'y':
            print("保持当前用户ID列表不变")
        else:
            new_users = input("请输入新的用户ID列表 (用逗号分隔): ").strip()
            if new_users:
                # 更新配置文件中的用户ID列表
                update_config_value("TELEGRAM_ALLOWED_USERS", new_users)
                print("用户ID列表已更新")
    else:
        new_users = input("请输入允许使用机器人的用户ID (用逗号分隔，留空表示允许所有用户): ").strip()
        if new_users:
            # 更新配置文件中的用户ID列表
            update_config_value("TELEGRAM_ALLOWED_USERS", new_users)
            print("用户ID列表已设置")
        else:
            print("警告: 未限制用户ID，所有用户都能使用机器人")

def update_config_value(key, value):
    """更新配置文件中的值"""
    # 获取配置文件路径
    config_file = project_root / "config" / "settings.py"
    
    if not config_file.exists():
        print(f"错误: 配置文件不存在 {config_file}")
        return False
    
    try:
        # 读取当前配置
        with open(config_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 找到并更新对应的行
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key} = "):
                if key == "TELEGRAM_ALLOWED_USERS":
                    # 对于用户ID列表，需要特殊处理分割逻辑
                    lines[i] = f'{key} = os.environ.get("{key}", "").split(",")\n'
                    # 同时也要更新环境变量
                    os.environ[key] = value
                else:
                    # 对于普通字符串值
                    lines[i] = f'{key} = os.environ.get("{key}", "{value}")\n'
                    # 同时也要更新环境变量
                    os.environ[key] = value
                updated = True
                break
        
        if not updated:
            # 如果没有找到对应的行，则在文件末尾添加
            if key == "TELEGRAM_ALLOWED_USERS":
                lines.append(f'{key} = os.environ.get("{key}", "").split(",")\n')
            else:
                lines.append(f'{key} = os.environ.get("{key}", "{value}")\n')
            os.environ[key] = value
        
        # 写回配置文件
        with open(config_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return True
    except Exception as e:
        print(f"更新配置文件失败: {e}")
        return False

def create_startup_script():
    """创建启动脚本"""
    print("\n创建启动脚本...")
    
    # 不同操作系统的启动脚本
    if sys.platform.startswith('win'):
        # Windows批处理脚本
        script_path = project_root / "scripts" / "start_telegram_bot.bat"
        script_content = f"""@echo off
cd {project_root}
python -m audioprocess.scripts.telegram_bot
pause
"""
    else:
        # Unix/Linux/Mac shell脚本
        script_path = project_root / "scripts" / "start_telegram_bot.sh"
        script_content = f"""#!/bin/bash
cd {project_root}
python -m audioprocess.scripts.telegram_bot
"""
    
    # 写入启动脚本
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # 设置可执行权限（仅Unix/Linux/Mac）
    if not sys.platform.startswith('win'):
        try:
            os.chmod(script_path, 0o755)
        except Exception as e:
            print(f"设置脚本执行权限失败: {e}")
    
    print(f"启动脚本已创建: {script_path}")

def main():
    """主函数"""
    print("=" * 50)
    print("Telegram YouTube字幕摘要机器人设置")
    print("=" * 50)
    
    parser = argparse.ArgumentParser(description="设置Telegram机器人")
    parser.add_argument("--skip-install", action="store_true", help="跳过依赖安装")
    args = parser.parse_args()
    
    # 安装依赖
    if not args.skip_install:
        if not install_dependencies():
            print("依赖安装失败，请手动安装python-telegram-bot==13.15")
    else:
        print("已跳过依赖安装")
    
    # 配置Telegram机器人
    configure_telegram_bot()
    
    # 创建启动脚本
    create_startup_script()
    
    print("\n设置完成！")
    print(f"可以使用以下命令启动机器人:")
    if sys.platform.startswith('win'):
        print(f"  {project_root}\\scripts\\start_telegram_bot.bat")
    else:
        print(f"  {project_root}/scripts/start_telegram_bot.sh")
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 