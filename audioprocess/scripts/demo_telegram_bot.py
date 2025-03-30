#!/usr/bin/env python3
"""
Telegram Bot 演示脚本
-------------------
演示如何通过代码设置和运行Telegram机器人
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root.parent))

# 导入必要的模块
from audioprocess.scripts.telegram_bot import main as run_telegram_bot
from audioprocess.config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def check_and_set_config():
    """检查并设置Telegram机器人配置"""
    # 检查Token
    if not TELEGRAM_BOT_TOKEN:
        token = input("请输入Telegram Bot Token: ").strip()
        if token:
            os.environ['TELEGRAM_BOT_TOKEN'] = token
            logger.info("已设置Bot Token")
        else:
            logger.error("未提供有效的Bot Token，机器人将无法启动")
            return False
    
    # 检查允许的用户ID
    if not TELEGRAM_ALLOWED_USERS or not TELEGRAM_ALLOWED_USERS[0]:
        user_input = input("请输入允许使用机器人的用户ID (用逗号分隔，留空表示允许所有用户): ").strip()
        if user_input:
            os.environ['TELEGRAM_ALLOWED_USERS'] = user_input
            logger.info(f"已设置允许的用户ID: {user_input}")
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("YouTube字幕摘要Telegram机器人演示")
    print("=" * 50)
    
    print("\n1. 检查配置...")
    if not check_and_set_config():
        print("配置检查失败，请修复问题后重试")
        return 1
    
    print("\n2. 启动Telegram机器人...")
    print("机器人启动后，您可以在Telegram中向机器人发送YouTube链接")
    print("按Ctrl+C可停止机器人")
    print("-" * 50)
    
    # 运行Telegram机器人
    try:
        return run_telegram_bot()
    except KeyboardInterrupt:
        print("\n收到停止信号，机器人已停止")
        return 0
    except Exception as e:
        logger.error(f"运行机器人时出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 