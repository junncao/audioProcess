#!/usr/bin/env python3
"""
空目录清理工具 - YouTube视频处理助手
----------------------------------
递归检查项目目录并删除空目录
"""

import os
import sys
import logging
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 需要检查的目录
DIRS_TO_CHECK = [
    os.path.join(ROOT_DIR, "audioprocess", "transcription_results"),
    os.path.join(ROOT_DIR, "audioprocess", "downloads"),
    os.path.join(ROOT_DIR, "audioprocess", "temp_subtitles"),
]

# 要忽略的目录（不会被删除，即使为空）
IGNORE_DIRS = [
    os.path.join(ROOT_DIR, "audioprocess", "transcription_results"),
    os.path.join(ROOT_DIR, "audioprocess", "downloads"),
    os.path.join(ROOT_DIR, "audioprocess", "temp_subtitles"),
]

def is_empty_dir(path):
    """检查目录是否为空"""
    return len(os.listdir(path)) == 0

def delete_empty_dirs(path, ignore_list):
    """递归删除空目录"""
    if not os.path.isdir(path):
        return 0
    
    # 如果目录在忽略列表中，则不删除，但仍递归检查子目录
    delete_allowed = path not in ignore_list
    
    # 获取目录中的所有内容
    contents = os.listdir(path)
    count = 0
    
    # 首先递归处理所有子目录
    for item in contents:
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            count += delete_empty_dirs(item_path, ignore_list)
    
    # 再次检查目录是否为空（子目录可能已被删除）
    if is_empty_dir(path) and delete_allowed:
        logger.info(f"删除空目录: {path}")
        os.rmdir(path)
        return count + 1
    
    return count

def main():
    """主函数"""
    print("YouTube视频处理助手 - 空目录清理工具")
    print("-------------------------------------")
    
    deleted_count = 0
    
    # 检查目录是否存在，不存在则创建
    for directory in DIRS_TO_CHECK:
        if not os.path.exists(directory):
            logger.info(f"创建目录: {directory}")
            os.makedirs(directory, exist_ok=True)
    
    # 递归删除空目录
    print("开始检查空目录...")
    for directory in DIRS_TO_CHECK:
        if os.path.isdir(directory):
            deleted_count += delete_empty_dirs(directory, IGNORE_DIRS)
    
    # 输出结果
    if deleted_count > 0:
        print(f"完成! 共删除了 {deleted_count} 个空目录。")
    else:
        print("完成! 没有发现需要删除的空目录。")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 