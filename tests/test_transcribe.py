#!/usr/bin/env python3
"""
测试文件 - 仅测试语音转录功能
-----------------------------
直接使用音频文件 URL 测试 DashScope 语音转录和文本摘要
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# 添加父目录到 Python 路径，以便导入父目录中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从主脚本导入函数
from main import transcribe_audio, RESULTS_DIR

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """主函数 - 仅用于测试转录和摘要功能"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试 DashScope 语音转录和文本摘要功能')
    parser.add_argument('--url', type=str, required=False, help='音频文件的 URL')
    parser.add_argument('--skip-summary', action='store_true', help='跳过文本摘要步骤')
    args = parser.parse_args()
    
    if not args.url:
        args.url = "https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav"
        logger.info(f"使用默认测试 URL: {args.url}")
    
    # 调用转录函数 - 直接使用主脚本中的函数
    logger.info(f"开始使用 URL 进行音频转录和摘要测试: {args.url}")
    result = transcribe_audio(args.url, skip_summary=args.skip_summary)
    
    # 打印结果
    print("\n---------------------------------------")
    
    if 'error' in result:
        print(f"处理失败: {result['error']}")
    else:
        print(f"语音识别结果:")
        print(result['full_text'])
        
        if 'summary' in result and result['summary']:
            print("\n文本摘要:")
            print(result['summary'])
        
        if 'saved_file' in result:
            print(f"\n结果已保存到: {result['saved_file']}")
            print(f"所有转录结果保存在目录: {RESULTS_DIR}")
    
    print("---------------------------------------\n")
    
    # 如果有错误，返回非零状态码
    return 0 if 'error' not in result else 1

if __name__ == "__main__":
    sys.exit(main()) 