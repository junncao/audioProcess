#!/usr/bin/env python3
"""
测试文件 - 仅测试 OSS 文件删除功能
---------------------------------
测试从阿里云 OSS 删除文件的功能
"""

import os
import sys
import logging
import argparse

# 添加父目录到 Python 路径，以便导入父目录中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从主脚本导入函数
from main import upload_file_to_oss, delete_file_from_oss

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_delete_file():
    """测试OSS文件删除功能"""
    # # 解析命令行参数
    # parser = argparse.ArgumentParser(description='测试 OSS 文件删除功能')
    # parser.add_argument('--file', type=str, required=True, help='要上传并删除的测试文件路径')
    # args = parser.parse_args()
    #
    # # 检查文件是否存在
    # if not os.path.exists(args.file):
    #     logger.error(f"文件不存在: {args.file}")
    #     return 1
    #
    # logger.info("=== 开始OSS文件删除测试 ===")
    #
    # # 步骤1: 先上传测试文件
    # logger.info(f"步骤1: 上传测试文件到OSS: {args.file}")
    # oss_url, object_name = upload_file_to_oss(args.file)
    #
    # if not oss_url or not object_name:
    #     logger.error("测试文件上传失败")
    #     return 1
    #
    # logger.info(f"文件上传成功: {object_name}")


    object_name = "audio_edtcimtl_20250329230549.webm"
    # 步骤2: 删除测试文件
    logger.info(f"步骤2: 从OSS删除文件: {object_name}")
    result = delete_file_from_oss(object_name)

    if result:
        logger.info("测试成功: 文件删除成功")
        print("\n---------------------------------------")
        print("OSS文件删除测试成功!")
        print(f"OSS对象名: {object_name}")
        print("---------------------------------------\n")
        return 0
    else:
        logger.error("测试失败: 文件删除失败")
        print("\n---------------------------------------")
        print("OSS文件删除测试失败!")
        print(f"OSS对象名: {object_name}")
        print("请检查日志获取详细信息")
        print("---------------------------------------\n")
        return 1


if __name__ == "__main__":
    sys.exit(test_delete_file())