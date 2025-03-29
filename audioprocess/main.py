#!/usr/bin/env python3
"""
YouTube 视频处理主程序
------------------
根据 YouTube URL 下载音频，提取字幕或转录音频，然后生成摘要

主要功能：
1. 从 YouTube 视频提取字幕（如果可用）
2. 或者下载音频并转录
3. 对字幕或转录内容生成摘要
"""

import os
import sys
import argparse

from audioprocess.utils.logger import get_logger
from audioprocess.utils.proxy_manager import disable_all_proxies
from audioprocess.utils.file_utils import read_text_file

from audioprocess.core.youtube_downloader import download_audio_from_youtube
from audioprocess.core.oss_uploader import upload_file_to_oss
from audioprocess.core.subtitle_extractor import extract_youtube_subtitles
from audioprocess.core.transcription import transcribe_audio
from audioprocess.core.summarization import summarize_text, save_summary_result

logger = get_logger(__name__)

def process_youtube_video(url, force_audio=False, skip_summary=False, youtube_proxy=None):
    """
    处理 YouTube 视频：尝试提取字幕，或下载音频并转录，然后生成摘要
    
    参数:
        url: YouTube 视频 URL
        force_audio: 是否强制使用音频下载和转录流程
        skip_summary: 是否跳过摘要步骤
        youtube_proxy: YouTube 下载专用代理
        
    返回:
        处理结果字典
    """
    result = {'success': False}
    
    # 1. 尝试提取字幕（除非强制使用音频流程）
    if not force_audio:
        logger.info("尝试从 YouTube 视频中提取字幕...")
        subtitle_result = extract_youtube_subtitles(url, proxy=youtube_proxy)
        
        if subtitle_result:
            logger.info(f"成功提取字幕，语言: {subtitle_result['language']}")
            result['subtitle_extracted'] = True
            result['text'] = subtitle_result['text']
            result['subtitle_file'] = subtitle_result['subtitle_file']
            result['language'] = subtitle_result['language']
            
            # 2. 对字幕内容生成摘要（除非指定跳过）
            if not skip_summary:
                logger.info("开始对字幕内容进行摘要...")
                summary = summarize_text(subtitle_result['text'])
                
                if summary and not summary.startswith("摘要生成失败"):
                    result['summary'] = summary
                    
                    # 保存字幕文本和摘要到结果文件
                    saved_file = save_summary_result(
                        subtitle_result['text'], 
                        summary, 
                        f"YouTube字幕: {url}"
                    )
                    
                    if saved_file:
                        result['summary_file'] = saved_file
                else:
                    result['summary_error'] = summary or "未能生成摘要"
            
            result['success'] = True
            return result
        else:
            logger.info("未找到字幕或提取失败，将使用音频下载和转录流程")
    
    # 3. 如果没有找到字幕或被指示使用音频流程，继续原有流程
    # 从 YouTube 下载音频
    audio_file = download_audio_from_youtube(url, proxy=youtube_proxy)
    if not audio_file:
        logger.error("音频下载失败")
        result['error'] = "音频下载失败"
        return result
    
    result['audio_file'] = audio_file
    
    # 4. 将音频文件上传到阿里云 OSS
    oss_url = upload_file_to_oss(audio_file)
    if not oss_url:
        logger.error("文件上传到 OSS 失败")
        result['error'] = "文件上传到 OSS 失败"
        return result
    
    result['oss_url'] = oss_url
    
    # 5. 转录音频文件
    transcription_result = transcribe_audio(oss_url)
    
    if 'error' in transcription_result:
        logger.error(f"音频转录失败: {transcription_result['error']}")
        result['error'] = f"音频转录失败: {transcription_result['error']}"
        return result
    
    result['text'] = transcription_result['full_text']
    result['transcription_file'] = transcription_result.get('saved_file')
    
    # 6. 对转录内容生成摘要（除非指定跳过）
    if not skip_summary:
        logger.info("开始对转录内容进行摘要...")
        summary = summarize_text(transcription_result['full_text'])
        
        if summary and not summary.startswith("摘要生成失败"):
            result['summary'] = summary
            
            # 保存转录文本和摘要到结果文件
            saved_file = save_summary_result(
                transcription_result['full_text'], 
                summary, 
                f"音频转录: {url}"
            )
            
            if saved_file:
                result['summary_file'] = saved_file
        else:
            result['summary_error'] = summary or "未能生成摘要"
    
    result['success'] = True
    return result

def process_direct_oss_url(oss_url, skip_summary=False):
    """
    直接处理 OSS URL：转录音频并生成摘要
    
    参数:
        oss_url: OSS 音频文件 URL
        skip_summary: 是否跳过摘要步骤
        
    返回:
        处理结果字典
    """
    result = {'success': False}
    
    # 1. 转录音频文件
    transcription_result = transcribe_audio(oss_url)
    
    if 'error' in transcription_result:
        logger.error(f"音频转录失败: {transcription_result['error']}")
        result['error'] = f"音频转录失败: {transcription_result['error']}"
        return result
    
    result['text'] = transcription_result['full_text']
    result['transcription_file'] = transcription_result.get('saved_file')
    
    # 2. 对转录内容生成摘要（除非指定跳过）
    if not skip_summary:
        logger.info("开始对转录内容进行摘要...")
        summary = summarize_text(transcription_result['full_text'])
        
        if summary and not summary.startswith("摘要生成失败"):
            result['summary'] = summary
            
            # 保存转录文本和摘要到结果文件
            saved_file = save_summary_result(
                transcription_result['full_text'], 
                summary, 
                f"OSS音频: {oss_url}"
            )
            
            if saved_file:
                result['summary_file'] = saved_file
        else:
            result['summary_error'] = summary or "未能生成摘要"
    
    result['success'] = True
    return result

def process_direct_text(text, source_description="直接文本输入"):
    """
    直接处理文本内容：生成摘要
    
    参数:
        text: 要摘要的文本内容
        source_description: 文本来源描述
        
    返回:
        处理结果字典
    """
    result = {'success': False}
    
    if not text:
        logger.error("无文本内容可供摘要")
        result['error'] = "无文本内容可供摘要"
        return result
    
    # 生成摘要
    logger.info("开始生成文本摘要...")
    summary = summarize_text(text)
    
    if not summary:
        logger.error("摘要生成失败: 未返回结果")
        result['error'] = "摘要生成失败: 未返回结果"
        return result
    elif summary.startswith("摘要生成失败"):
        logger.error(f"摘要生成失败: {summary}")
        result['error'] = summary
        return result
    
    result['text'] = text
    result['summary'] = summary
    
    # 保存原文和摘要到结果文件
    saved_file = save_summary_result(text, summary, source_description)
    
    if saved_file:
        result['summary_file'] = saved_file
    
    result['success'] = True
    return result

def print_result(result):
    """
    打印处理结果
    
    参数:
        result: 处理结果字典
    """
    print("\n---------------------------------------")
    
    if not result['success']:
        print(f"处理失败: {result.get('error', '未知错误')}")
        print("---------------------------------------\n")
        return
    
    # 如果有字幕或音频文件，则显示
    if 'subtitle_extracted' in result and result['subtitle_extracted']:
        print(f"已提取 YouTube 字幕，语言: {result.get('language', '未知')}")
        print(f"字幕文件保存于: {result.get('subtitle_file', '未知')}")
    elif 'audio_file' in result:
        print(f"已下载音频: {result['audio_file']}")
        
        if 'oss_url' in result:
            print(f"已上传到 OSS，URL: {result['oss_url']}")
    
    # 显示文本内容（截断）
    if 'text' in result:
        print("\n原始文本片段:")
        text = result['text']
        # 只显示前300个字符
        display_text = text[:300] + ("..." if len(text) > 300 else "")
        print(display_text)
        
        if 'transcription_file' in result:
            print(f"\n完整转录保存于: {result['transcription_file']}")
    
    # 显示摘要
    if 'summary' in result:
        print("\n文本摘要:")
        print(result['summary'])
        
        if 'summary_file' in result:
            print(f"\n完整摘要和原文保存于: {result['summary_file']}")
    elif 'summary_error' in result:
        print("\n摘要生成失败:")
        print(result['summary_error'])
    
    print("---------------------------------------\n")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='YouTube 视频处理工具：提取字幕/转录音频并生成摘要')
    
    # YouTube相关参数
    parser.add_argument('--url', type=str, help='YouTube 视频 URL')
    parser.add_argument('--youtube-proxy', type=str, help='YouTube下载专用代理，格式如http://127.0.0.1:7890')
    parser.add_argument('--force-audio', action='store_true', help='强制使用音频下载和转录流程，即使有字幕')
    
    # OSS直接测试参数
    parser.add_argument('--oss-url', type=str, help='OSS 音频文件 URL, 直接用于语音识别测试')
    
    # 文本直接测试参数
    parser.add_argument('--text', type=str, help='直接输入要摘要的文本内容')
    parser.add_argument('--text-file', type=str, help='包含要摘要的文本文件路径')
    
    # 其他选项
    parser.add_argument('--skip-summary', action='store_true', help='跳过文本摘要步骤')
    parser.add_argument('--no-proxy', action='store_true', help='禁用所有代理设置')
    
    args = parser.parse_args()
    
    # 处理全局代理设置
    if args.no_proxy:
        disable_all_proxies()
    
    # 1. 优先处理直接文本输入
    if args.text or args.text_file:
        text_to_summarize = None
        source_description = None
        
        if args.text:
            # 直接使用提供的文本
            logger.info("使用命令行参数提供的文本进行摘要测试")
            text_to_summarize = args.text
            source_description = "命令行输入文本"
        elif args.text_file:
            # 从文件读取文本
            logger.info(f"从文件读取文本进行摘要测试: {args.text_file}")
            text_to_summarize = read_text_file(args.text_file)
            source_description = f"文件: {args.text_file}"
            
            if not text_to_summarize:
                logger.error(f"无法读取文件: {args.text_file}")
                return 1
        
        # 处理文本并生成摘要
        result = process_direct_text(text_to_summarize, source_description)
        print_result(result)
        return 0 if result['success'] else 1
    
    # 2. 处理 OSS URL 直接测试
    if args.oss_url:
        logger.info(f"直接使用 OSS URL 进行语音识别测试: {args.oss_url}")
        result = process_direct_oss_url(args.oss_url, skip_summary=args.skip_summary)
        print_result(result)
        return 0 if result['success'] else 1
    
    # 3. 处理 YouTube URL
    if args.url:
        youtube_url = args.url
    else:
        # 使用测试 URL
        youtube_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # YouTube 第一个视频
        logger.info(f"使用测试 URL: {youtube_url}")
    
    # 处理 YouTube 视频
    result = process_youtube_video(
        youtube_url,
        force_audio=args.force_audio,
        skip_summary=args.skip_summary,
        youtube_proxy=args.youtube_proxy
    )
    
    print_result(result)
    return 0 if result['success'] else 1

if __name__ == "__main__":
    sys.exit(main()) 