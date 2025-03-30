#!/usr/bin/env python3
"""
YouTube视频处理助手 - Telegram机器人启动脚本
-------------------------------------------
这是一个简单的入口点脚本，用于从项目根目录启动Telegram机器人服务。
提供更方便的启动方式：`python telegram_bot.py`
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """从项目根目录启动Telegram机器人服务"""
    try:
        # 确保必要目录存在
        os.makedirs("audioprocess/transcription_results", exist_ok=True)
        os.makedirs("audioprocess/downloads", exist_ok=True)
        os.makedirs("audioprocess/temp_subtitles", exist_ok=True)
        
        # 导入并启动机器人模块
        logger.info("正在启动YouTube视频处理助手Telegram机器人...")
        
        # 导入机器人主模块并运行
        from audioprocess.scripts.telegram_bot import main as bot_main
        return bot_main()
        
    except ImportError:
        logger.error("无法导入机器人模块。请确保已安装所有依赖，并且项目结构正确。")
        logger.error("请执行: pip install -r requirements.txt")
        return 1
    except Exception as e:
        logger.error(f"启动过程中发生错误: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 