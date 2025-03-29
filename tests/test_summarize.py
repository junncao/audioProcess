#!/usr/bin/env python3
"""
测试文件 - 仅测试文本摘要功能
----------------------------
使用阿里云 DashScope 的 Qwen 大模型对文本内容进行摘要总结
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# 添加父目录到 Python 路径，以便导入父目录中的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从主脚本导入函数
from main import summarize_text, save_transcription_result, RESULTS_DIR

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def read_text_from_file(file_path):
    """从文件中读取文本内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件时出错: {str(e)}")
        return None

def main():
    """主函数 - 仅用于测试文本摘要功能"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试 DashScope Qwen 文本摘要功能')
    parser.add_argument('--file', type=str, help='包含要摘要的文本的文件路径')
    parser.add_argument('--text', type=str, help='直接提供要摘要的文本')
    parser.add_argument('--transcription-file', type=str, help='从转录结果文件中提取文本进行摘要')
    parser.add_argument('--no-proxy', action='store_true', help='禁用所有代理设置')
    args = parser.parse_args()
    
    # 处理代理设置 - 文本摘要功能默认禁用代理
    # 将no-proxy默认设为True，不再需要显式指定
    logger.info("摘要功能默认禁用代理设置")
    # 清除可能的代理环境变量
    original_proxies = {}
    for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy']:
        if proxy_var in os.environ:
            original_proxies[proxy_var] = os.environ[proxy_var]
            del os.environ[proxy_var]
    # 设置空代理
    os.environ['NO_PROXY'] = '*'
    
    # 获取要摘要的文本内容
    text_to_summarize = None
    source_description = None
    
    if args.file:
        # 从文件读取文本
        logger.info(f"从文件读取文本: {args.file}")
        text_to_summarize = read_text_from_file(args.file)
        source_description = f"文件: {args.file}"
        
    elif args.text:
        # 直接使用提供的文本
        logger.info("使用命令行参数提供的文本")
        text_to_summarize = args.text
        source_description = "直接输入的文本"
        
    elif args.transcription_file:
        # 从转录结果文件中提取文本
        logger.info(f"从转录结果文件中提取文本: {args.transcription_file}")
        if os.path.exists(args.transcription_file):
            content = read_text_from_file(args.transcription_file)
            
            # 尝试从转录文件中提取文本部分
            if "==== 转录文本 ====" in content:
                parts = content.split("==== 转录文本 ====", 1)
                if len(parts) > 1:
                    text_section = parts[1]
                    if "==== 文本摘要 ====" in text_section:
                        text_to_summarize = text_section.split("==== 文本摘要 ====", 1)[0].strip()
                    else:
                        text_to_summarize = text_section.strip()
                    
                    source_description = f"转录文件: {args.transcription_file}"
        else:
            logger.error(f"转录文件不存在: {args.transcription_file}")
    
    else:
        # 如果没有提供文本，使用示例文本
        logger.info("未提供文本，使用示例文本")
        text_to_summarize = """
人工智能(AI)是一个广泛的领域，涵盖了机器学习、深度学习、自然语言处理、计算机视觉等多个分支。机器学习是AI的核心技术之一，它使计算机系统能够通过经验自动改进。
深度学习是机器学习的一个子集，它使用多层神经网络来模拟人脑的学习过程。
自然语言处理(NLP)使计算机能够理解、解释和生成人类语言。计算机视觉则让机器能够从图像或视频中获取信息并理解内容。
AI技术已经在各行各业得到了广泛应用，包括医疗健康、金融、交通、零售、教育等领域。在医疗领域，AI可以帮助诊断疾病、预测患者风险和发现新的治疗方法。
在金融行业，AI被用于欺诈检测、算法交易和个性化金融服务。在交通领域，AI推动了自动驾驶技术的发展。
虽然AI带来了巨大的好处，但也面临着诸如数据隐私、算法偏见、安全风险和就业转型等挑战。为了解决这些问题，研究者和政策制定者正在努力开发更透明、公平和安全的AI系统。
未来，随着技术的不断进步，AI将会变得更加智能和自主，有可能在更多领域产生革命性的影响。
        """
        source_description = "示例文本"
    
    if not text_to_summarize:
        logger.error("无法获取要摘要的文本内容")
        return 1
    
    # 调用摘要函数
    logger.info("开始生成文本摘要...")
    summary = summarize_text(text_to_summarize)
    
    if not summary or summary.startswith("摘要生成失败"):
        logger.error(f"摘要生成失败: {summary}")
        print("\n---------------------------------------")
        print("文本摘要生成失败。")
        print(f"错误信息: {summary}")
        print("---------------------------------------\n")
        return 1
    
    # 保存摘要结果到文件
    saved_file = save_transcription_result(text_to_summarize, summary, None, "summary")
    
    # 打印结果
    print("\n---------------------------------------")
    print(f"源文本 ({source_description}):")
    print("---------------------------------------")
    # 只打印前200个字符，然后是省略号
    if len(text_to_summarize) > 200:
        print(f"{text_to_summarize[:200]}...(省略{len(text_to_summarize)-200}个字符)")
    else:
        print(text_to_summarize)
    
    print("\n---------------------------------------")
    print("生成的摘要:")
    print("---------------------------------------")
    print(summary)
    
    if saved_file:
        print(f"\n完整结果已保存到: {saved_file}")
    
    print("---------------------------------------\n")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 