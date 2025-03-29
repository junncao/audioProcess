#!/usr/bin/env python3
"""
测试文件 - 仅测试 YouTube 音频下载功能
---------------------------------
从 YouTube 下载视频的音频部分
"""

import os
import sys
import logging
import argparse

# 添加父目录到 Python 路径，以便导入父目录中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从主脚本导入函数
from main import download_audio_from_youtube

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """主函数 - 仅用于测试YouTube下载功能"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试 YouTube 音频下载功能')
    parser.add_argument('--url', type=str, help='YouTube 视频 URL')
    parser.add_argument('--output', type=str, default='./downloads', help='下载文件保存路径')
    args = parser.parse_args()
    
    # 使用默认测试 URL 或命令行参数提供的 URL
    url = args.url if args.url else "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    # 如果没有提供 URL，记录使用默认 URL
    if not args.url:
        logger.info(f"使用默认测试 URL: {url}")
        
    logger.info(f"开始测试从YouTube下载音频: {url}")
    
    # 调用下载函数 - 直接使用主脚本中的函数
    audio_file = download_audio_from_youtube(url, args.output)
    
    if audio_file:
        # 打印结果
        print("\n---------------------------------------")
        print(f"音频下载成功!")
        print(f"文件保存路径: {audio_file}")
        print("---------------------------------------\n")
        return 0
    else:
        print("\n下载失败，请检查日志获取详细信息\n")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 