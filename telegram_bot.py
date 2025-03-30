#!/usr/bin/env python3
"""
YouTube字幕摘要Telegram机器人启动器
---------------------------------
从项目根目录直接启动Telegram机器人
"""

import os
import sys

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入机器人主函数
from audioprocess.scripts.telegram_bot import main

if __name__ == "__main__":
    sys.exit(main()) 