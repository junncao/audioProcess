#!/usr/bin/env python3
"""
测试文件 - 仅测试 OSS 上传功能
-----------------------------
上传本地音频文件到阿里云 OSS
"""

import os
import sys
import logging
import argparse

# 添加父目录到 Python 路径，以便导入父目录中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从主脚本导入函数
from main import upload_file_to_oss

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """主函数 - 仅用于测试OSS上传功能"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试 OSS 上传功能')
    parser.add_argument('--file', type=str, required=True, help='要上传的本地音频文件路径')
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.file):
        logger.error(f"文件不存在: {args.file}")
        return 1
    
    logger.info(f"开始测试上传文件到OSS: {args.file}")
    
    # 调用上传函数 - 直接使用主脚本中的函数
    oss_url, object_name = upload_file_to_oss(args.file)
    
    if oss_url:
        # 打印结果
        print("\n---------------------------------------")
        print(f"文件上传成功!")
        print(f"OSS URL (24小时有效):")
        print(oss_url)
        print("---------------------------------------\n")
        return 0
    else:
        print("\n上传失败，请检查日志获取详细信息\n")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 