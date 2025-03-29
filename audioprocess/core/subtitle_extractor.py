#!/usr/bin/env python3
"""
YouTube 字幕提取模块
-----------------
提供从YouTube视频中提取字幕的功能
"""

import os
import json
import requests
from datetime import datetime
import yt_dlp

from audioprocess.utils.logger import get_logger
from audioprocess.utils.proxy_manager import get_http_proxy
from audioprocess.config.settings import TEMP_DIR, RESULTS_DIR, SUPPORTED_LANGUAGES

logger = get_logger(__name__)

class SubtitleExtractor:
    """YouTube字幕提取器类"""
    
    def __init__(self, temp_dir=None, proxy=None):
        """
        初始化字幕提取器
        
        参数:
            temp_dir: 临时文件目录，默认使用配置中的临时目录
            proxy: 可选的代理设置
        """
        self.temp_dir = temp_dir or TEMP_DIR
        self.proxy = proxy
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def extract(self, url):
        """
        从YouTube视频中提取字幕
        
        参数:
            url: YouTube视频URL
            
        返回:
            字典，包含提取到的字幕文本和语言信息，如果没有字幕则返回None
        """
        if not url or not url.strip():
            logger.error("无效的URL")
            return None
        
        try:
            logger.info(f"尝试从视频中提取字幕: {url}")
            
            # 配置yt-dlp选项 - 只获取字幕信息，不下载视频
            ydl_opts = self._get_ydl_opts()
            
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
                
                # 获取字幕信息
                subtitles_info = self._find_best_subtitle(info)
                if not subtitles_info:
                    return None
                
                # 下载和解析字幕
                subtitle_content = self._download_subtitle(subtitles_info['url'])
                if not subtitle_content:
                    return None
                
                # 解析字幕内容
                subtitle_text = self._parse_subtitle(subtitle_content, subtitles_info['format'])
                if not subtitle_text:
                    return None
                
                # 保存字幕文本到文件
                subtitle_file = self._save_subtitle(
                    subtitle_text, 
                    url, 
                    subtitles_info['language'], 
                    subtitles_info['format']
                )
                
                # 返回字幕信息
                return {
                    'text': subtitle_text,
                    'language': subtitles_info['language'],
                    'format': subtitles_info['format'],
                    'subtitle_file': subtitle_file,
                    'video_url': url
                }
                
        except Exception as e:
            logger.error(f"提取字幕时出错: {str(e)}")
            return None
    
    def _get_ydl_opts(self):
        """获取yt-dlp选项配置"""
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': SUPPORTED_LANGUAGES,  # 优先中文，其次英文
            'subtitlesformat': 'best',
            'quiet': False,
            'no_warnings': False,
            'cookiesfrombrowser': ('chrome',),
            'paths': {'home': self.temp_dir}
        }
        
        # 处理代理设置
        proxy = get_http_proxy(self.proxy)
        if proxy:
            ydl_opts['proxy'] = proxy
        
        return ydl_opts
    
    def _find_best_subtitle(self, info):
        """
        从视频信息中找到最佳的字幕
        
        参数:
            info: 视频信息字典
            
        返回:
            字典，包含字幕URL、语言和格式，如果没有合适的字幕则返回None
        """
        # 优先使用手动添加的字幕，其次使用自动生成的字幕
        subtitles_dict = info.get('subtitles', {}) or info.get('automatic_captions', {})
        
        if not subtitles_dict:
            logger.info("未找到任何字幕")
            return None
        
        # 按优先级查找字幕语言
        selected_lang = None
        for lang in SUPPORTED_LANGUAGES:
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
        
        return {
            'url': subtitle_url,
            'language': selected_lang,
            'format': selected_format
        }
    
    def _download_subtitle(self, url):
        """
        下载字幕内容
        
        参数:
            url: 字幕URL
            
        返回:
            字幕内容文本或None（如果下载失败）
        """
        try:
            logger.info(f"开始下载字幕: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"下载字幕失败: {str(e)}")
            return None
    
    def _parse_subtitle(self, content, format_type):
        """
        解析字幕内容
        
        参数:
            content: 字幕内容文本
            format_type: 字幕格式
            
        返回:
            解析后的纯文本字幕或None（如果解析失败）
        """
        if not content:
            return None
        
        try:
            # 根据字幕格式选择不同的解析方法
            if format_type == 'json3':
                return self._parse_json_subtitle(content)
            else:
                return self._parse_text_subtitle(content)
        except Exception as e:
            logger.error(f"解析字幕失败: {str(e)}")
            return None
    
    def _parse_json_subtitle(self, content):
        """解析JSON格式的字幕"""
        json_data = json.loads(content)
        events = json_data.get('events', [])
        subtitle_text = ""
        
        for event in events:
            if 'segs' in event:
                for seg in event['segs']:
                    if 'utf8' in seg:
                        subtitle_text += seg['utf8'] + " "
        
        subtitle_text = subtitle_text.strip()
        
        if not subtitle_text:
            logger.error("提取的字幕内容为空")
            return None
            
        return subtitle_text
    
    def _parse_text_subtitle(self, content):
        """解析文本格式的字幕（VTT、SRT等）"""
        lines = content.split('\n')
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
            
        return subtitle_text
    
    def _save_subtitle(self, text, video_url, language, format_type):
        """
        保存字幕到文件
        
        参数:
            text: 字幕文本
            video_url: 视频URL
            language: 字幕语言
            format_type: 字幕格式
            
        返回:
            保存的文件路径
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"subtitle_{language}_{timestamp}.txt"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"YouTube视频: {video_url}\n字幕语言: {language}\n字幕格式: {format_type}\n\n")
                f.write(text)
            
            logger.info(f"字幕内容已保存至: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存字幕失败: {str(e)}")
            return None

# 方便直接使用的函数
def extract_youtube_subtitles(url, proxy=None):
    """
    从YouTube视频中提取字幕的便捷函数
    
    参数:
        url: YouTube视频URL
        proxy: 可选的代理设置
        
    返回:
        字典，包含提取到的字幕文本和语言信息，如果没有字幕则返回None
    """
    extractor = SubtitleExtractor(proxy=proxy)
    return extractor.extract(url) 