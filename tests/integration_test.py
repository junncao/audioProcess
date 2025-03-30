#!/usr/bin/env python3
"""
集成测试脚本 - 音频处理流程
---------------------------
这个脚本整合了整个音频处理流程的各个部分，包括：
1. 从YouTube下载音频
2. 将音频上传到阿里云OSS
3. 使用DashScope API进行语音识别
4. 使用Qwen大模型进行文本摘要

可以通过命令行参数选择执行完整流程或仅特定步骤。
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 确保结果目录存在
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "transcription_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# 导入所需函数
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main
from youtube_audio_downloader import download_audio

def main_function():
    """集成测试主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='音频处理流程集成测试')
    parser.add_argument('--youtube-url', type=str, help='YouTube视频URL')
    parser.add_argument('--audio-file', type=str, help='本地音频文件路径')
    parser.add_argument('--oss-url', type=str, help='OSS音频文件URL')
    parser.add_argument('--skip-download', action='store_true', help='跳过YouTube下载步骤')
    parser.add_argument('--skip-upload', action='store_true', help='跳过OSS上传步骤')
    parser.add_argument('--skip-transcribe', action='store_true', help='跳过语音识别步骤')
    parser.add_argument('--skip-summary', action='store_true', help='跳过文本摘要步骤')
    parser.add_argument('--no-proxy', action='store_true', help='完全禁用所有代理设置')
    parser.add_argument('--youtube-proxy', type=str, help='仅用于YouTube下载的代理地址，格式如http://127.0.0.1:7890')
    args = parser.parse_args()

    # 保存原始代理设置
    original_proxies = {}
    for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy']:
        if proxy_var in os.environ:
            original_proxies[proxy_var] = os.environ[proxy_var]

    # 处理代理设置
    if args.no_proxy:
        logger.info("完全禁用所有代理设置")
        # 清除所有代理环境变量
        for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
        # 设置空代理
        os.environ['NO_PROXY'] = '*'
    
    # 检查执行路径和选项
    audio_file = args.audio_file
    oss_url = args.oss_url
    youtube_url = args.youtube_url
    
    # 步骤1: 从YouTube下载音频(如果需要)
    if not args.skip_download and youtube_url and not audio_file:
        logger.info(f"开始从YouTube下载音频: {youtube_url}")
        
        # 为YouTube下载单独设置代理
        if args.youtube_proxy and not args.no_proxy:
            logger.info(f"为YouTube下载设置专用代理: {args.youtube_proxy}")
            for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY']:
                os.environ[proxy_var] = args.youtube_proxy
            os.environ['http_proxy'] = args.youtube_proxy
            os.environ['https_proxy'] = args.youtube_proxy
        
        # 下载音频
        audio_file = download_audio(youtube_url)
        
        # 下载完成后，如果不是完全禁用代理，则恢复原始代理设置
        if not args.no_proxy:
            for proxy_var, value in original_proxies.items():
                os.environ[proxy_var] = value
        
        if not audio_file:
            logger.error("音频下载失败，退出测试")
            return 1
        logger.info(f"音频下载成功: {audio_file}")
    
    # 步骤2: 上传到OSS(如果需要)
    if not args.skip_upload and audio_file and not oss_url:
        logger.info(f"开始将音频文件上传到OSS: {audio_file}")
        # 直接使用main.py中的upload_file_to_oss函数
        oss_url, object_name = main.upload_file_to_oss(audio_file)
        if not oss_url:
            logger.error("OSS上传失败，退出测试")
            return 1
        logger.info(f"OSS上传成功: {oss_url}")
    
    # 步骤3: 转录音频(如果需要)
    if not args.skip_transcribe and oss_url:
        logger.info(f"开始转录音频: {oss_url}")
        # main.py中的transcribe_audio函数会自动管理摘要功能的代理设置
        transcription_result = main.transcribe_audio(oss_url, skip_summary=args.skip_summary)
        
        if 'error' in transcription_result:
            logger.error(f"音频转录失败: {transcription_result['error']}")
            return 1
            
        # 打印转录结果
        print("\n---------------------------------------")
        print("语音识别结果:")
        print(transcription_result['full_text'])
        
        if 'summary' in transcription_result and transcription_result['summary']:
            print("\n文本摘要:")
            print(transcription_result['summary'])
        
        if 'saved_file' in transcription_result:
            print(f"\n结果已保存到: {transcription_result['saved_file']}")
            
        print("---------------------------------------\n")
    
    # 如果没有执行任何步骤，打印帮助信息
    if (args.skip_download or not youtube_url) and (args.skip_upload or not audio_file) and (args.skip_transcribe or not oss_url):
        logger.warning("未执行任何操作 - 请提供至少一个有效的输入参数并启用相应步骤")
        parser.print_help()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main_function()) 