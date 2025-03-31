#!/usr/bin/env python3
"""
YouTube工具函数
--------------
提供YouTube URL验证和音频下载功能
"""

import os
import re
import logging
import yt_dlp
from audioprocess.config.settings import DOWNLOADS_DIR, DEFAULT_PROXY

# 配置日志
logger = logging.getLogger(__name__)

def is_youtube_url(url):
    """
    检查URL是否是有效的YouTube链接
    
    参数:
        url: 待检查的URL
        
    返回:
        bool: 是否是有效的YouTube链接
    """
    if not url:
        return False
    
    # 记录正在检查的URL
    logger.debug(f"检查URL是否为YouTube链接: {url}")
    
    # YouTube URL正则表达式模式 - 支持多种YouTube URL格式
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/live/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    
    # 检查是否匹配
    match = re.search(youtube_regex, url)
    result = bool(match)
    
    # 记录检查结果
    if result:
        logger.info(f"URL是有效的YouTube链接: {url}")
    else:
        logger.warning(f"URL不是有效的YouTube链接: {url}")
    
    return result

def download_audio(url, output_path=None, proxy=None):
    """
    从YouTube下载音频
    
    参数:
        url: YouTube视频URL
        output_path: 输出目录，默认为配置的下载目录
        proxy: 代理设置，默认使用配置中的代理
        
    返回:
        str: 下载的音频文件路径或None(如果下载失败)
    """
    if not url or not url.strip():
        logger.error("无效的URL")
        return None
    
    try:
        # 使用配置的下载目录或指定的输出目录
        output_dir = output_path or DOWNLOADS_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"开始从URL下载音频: {url}")
        logger.info(f"输出目录: {output_dir}")
        
        # 配置yt-dlp选项 - 简化配置，直接下载最佳音频
        ydl_opts = {
            'format': 'bestaudio/best',  # 最佳音频质量
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'cookiesfrombrowser': ('chrome',),
            # 移除后处理器配置，直接下载原始格式
            'ignoreerrors': True,
            'verbose': True,  # 添加详细日志，帮助诊断问题
        }
        
        # 处理代理设置
        if proxy:
            logger.info(f"使用提供的代理: {proxy}")
            ydl_opts['proxy'] = proxy
        elif os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
            system_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            logger.info(f"使用系统代理: {system_proxy}")
            ydl_opts['proxy'] = system_proxy
        else:
            logger.info(f"使用默认代理: {DEFAULT_PROXY}")
            ydl_opts['proxy'] = DEFAULT_PROXY
        
        # 下载音频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("开始提取视频信息并下载...")
            # 提取视频信息并下载
            info = ydl.extract_info(url, download=True)
            
            if not info:
                logger.error("无法获取视频信息")
                return None
            
            # 记录视频信息
            logger.info(f"成功获取视频信息: {info.get('title', '未知标题')}")
            
            # 获取下载的文件名
            if 'entries' in info:  # 播放列表
                if not info['entries']:
                    logger.error("播放列表为空")
                    return None
                logger.info("检测到播放列表，使用第一个视频")
                info = info['entries'][0]  # 获取第一个视频
            
            # 获取文件路径
            file_path = ydl.prepare_filename(info)
            logger.info(f"准备的文件名: {file_path}")
            
            # 检查文件是否存在
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                logger.info(f"下载完成，文件路径: {file_path}")
                logger.info(f"文件大小: {size/1024/1024:.2f} MB")
                return file_path
            
            # 如果没有找到原始文件，尝试检查其他扩展名
            base_path = os.path.splitext(file_path)[0]
            possible_extensions = ['.webm', '.mp3', '.m4a', '.mp4', '.ogg', '.opus']
            
            for ext in possible_extensions:
                possible_path = f"{base_path}{ext}"
                if os.path.exists(possible_path):
                    size = os.path.getsize(possible_path)
                    logger.info(f"找到文件，路径: {possible_path}")
                    logger.info(f"文件大小: {size/1024/1024:.2f} MB")
                    return possible_path
            
            # 如果没有找到文件，记录目录内容以便调试
            logger.error(f"找不到下载的文件，检查目录内容: {output_dir}")
            for file in os.listdir(output_dir):
                logger.info(f"目录中的文件: {file}")
            
            return None
    
    except Exception as e:
        logger.error(f"下载音频时出错: {str(e)}", exc_info=True)
        return None

def extract_youtube_subtitles(url, proxy=None):
    """
    从YouTube视频中提取字幕（优先中文，其次英文）
    
    参数:
        url: YouTube视频URL
        proxy: 可选的代理设置
        
    返回:
        字典，包含提取到的字幕文本和语言信息，如果没有字幕则返回None
    """
    if not url or not url.strip():
        logger.error("无效的URL")
        return None
    
    try:
        logger.info(f"尝试从视频中提取字幕: {url}")
        
        # 配置yt-dlp选项 - 只获取字幕信息，不下载视频
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh-Hans', 'zh-CN', 'zh', 'en'],  # 优先中文，其次英文
            'subtitlesformat': 'best',
            'quiet': False,
            'no_warnings': False,
            'cookiesfrombrowser': ('chrome',),
        }
        
        # 处理代理设置
        if proxy:
            logger.info(f"使用提供的代理: {proxy}")
            ydl_opts['proxy'] = proxy
        elif os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
            system_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            logger.info(f"使用系统代理: {system_proxy}")
            ydl_opts['proxy'] = system_proxy
        else:
            default_proxy = 'http://127.0.0.1:63618'
            logger.info(f"未找到系统代理，使用默认代理: {default_proxy}")
            ydl_opts['proxy'] = default_proxy
        
        # 创建临时目录存放字幕文件
        from audioprocess.config.settings import TEMP_DIR
        ydl_opts['paths'] = {'home': TEMP_DIR}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 提取视频信息，包括字幕
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error("无法获取视频信息")
                return None
            
            # 检查是否有字幕可用
            if not info.get('subtitles') and not info.get('automatic_captions'):
                logger.info("该视频没有可用的字幕（手动或自动）")
                return None
            
            # 优先使用手动添加的字幕，其次使用自动生成的字幕
            subtitles_dict = info.get('subtitles', {}) or info.get('automatic_captions', {})
            
            if not subtitles_dict:
                logger.info("未找到任何字幕")
                return None
            
            # 按优先级查找字幕语言
            preferred_langs = ['zh-Hans', 'zh-CN', 'zh', 'en']
            selected_lang = None
            
            for lang in preferred_langs:
                if lang in subtitles_dict and subtitles_dict[lang]:
                    selected_lang = lang
                    break
            
            if not selected_lang:
                # 如果没有找到首选语言，使用第一个可用的语言
                available_langs = list(subtitles_dict.keys())
                if available_langs:
                    selected_lang = available_langs[0]
                else:
                    logger.info("未找到任何字幕语言")
                    return None
            
            # 获取字幕下载链接
            logger.info(f"找到字幕，语言: {selected_lang}")
            subtitle_formats = subtitles_dict[selected_lang]
            
            # 优先选择文本格式的字幕
            preferred_formats = ['vtt', 'ttml', 'srv3', 'srv2', 'srv1', 'json3']
            selected_format = None
            subtitle_url = None
            
            for fmt in preferred_formats:
                for subtitle in subtitle_formats:
                    if subtitle.get('ext') == fmt:
                        selected_format = fmt
                        subtitle_url = subtitle.get('url')
                        break
                if selected_format:
                    break
            
            if not subtitle_url:
                # 如果没有找到首选格式，使用第一个可用的格式
                if subtitle_formats and 'url' in subtitle_formats[0]:
                    subtitle_url = subtitle_formats[0]['url']
                    selected_format = subtitle_formats[0].get('ext', 'unknown')
                else:
                    logger.error("无法获取字幕下载链接")
                    return None
            
            # 下载字幕
            logger.info(f"开始下载{selected_format}格式的{selected_lang}字幕...")
            try:
                import requests
                import json
                
                response = requests.get(subtitle_url, timeout=30)
                response.raise_for_status()
                subtitle_content = response.text
                
                # 解析不同格式的字幕内容
                if selected_format == 'json3':
                    # 解析JSON格式字幕
                    try:
                        json_data = json.loads(subtitle_content)
                        events = json_data.get('events', [])
                        subtitle_text = ""
                        
                        for event in events:
                            if 'segs' in event:
                                for seg in event['segs']:
                                    if 'utf8' in seg:
                                        subtitle_text += seg['utf8'] + " "
                        
                        subtitle_text = subtitle_text.strip()
                    except Exception as e:
                        logger.error(f"解析JSON字幕失败: {str(e)}")
                        return None
                else:
                    # 使用简单方法提取文本（适用于VTT、SRT等格式）
                    lines = subtitle_content.split('\n')
                    subtitle_text = ""
                    
                    for line in lines:
                        # 跳过时间戳和元数据行
                        if '-->' in line or line.strip().isdigit() or not line.strip():
                            continue
                        # 跳过WebVTT头部
                        if 'WEBVTT' in line:
                            continue
                        # 保留文本内容
                        subtitle_text += line.strip() + " "
                    
                    subtitle_text = subtitle_text.strip()
                
                if not subtitle_text:
                    logger.error("提取的字幕内容为空")
                    return None
                
                logger.info(f"成功提取字幕，内容长度: {len(subtitle_text)} 字符")
                
                # 保存字幕文本到文件（用于调试）
                import datetime
                from audioprocess.config.settings import RESULTS_DIR
                subtitle_file = os.path.join(RESULTS_DIR, f"subtitle_{selected_lang}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
                with open(subtitle_file, 'w', encoding='utf-8') as f:
                    f.write(f"YouTube视频: {url}\n字幕语言: {selected_lang}\n字幕格式: {selected_format}\n\n")
                    f.write(subtitle_text)
                
                logger.info(f"字幕内容已保存至: {subtitle_file}")
                
                return {
                    'text': subtitle_text,
                    'language': selected_lang,
                    'format': selected_format,
                    'subtitle_file': subtitle_file,
                    'video_url': url
                }
                
            except requests.exceptions.RequestException as e:
                logger.error(f"下载字幕失败: {str(e)}")
                return None
            
    except Exception as e:
        logger.error(f"提取字幕时出错: {str(e)}")
        return None 