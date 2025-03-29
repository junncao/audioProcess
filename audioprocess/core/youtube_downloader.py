#!/usr/bin/env python3
"""
YouTube 音频下载模块
-----------------
提供从YouTube下载音频的功能
"""

import os
import yt_dlp
from pathlib import Path

from audioprocess.utils.logger import get_logger
from audioprocess.utils.proxy_manager import get_http_proxy
from audioprocess.config.settings import DOWNLOADS_DIR

logger = get_logger(__name__)

class YouTubeDownloader:
    """YouTube音频下载器类"""
    
    def __init__(self, output_path=None, proxy=None):
        """
        初始化下载器
        
        参数:
            output_path: 下载文件保存路径，默认使用配置中的下载目录
            proxy: 可选的代理设置，格式如http://127.0.0.1:7890
        """
        self.output_path = output_path or DOWNLOADS_DIR
        self.proxy = proxy
        
        # 确保输出目录存在
        os.makedirs(self.output_path, exist_ok=True)
    
    def download(self, url):
        """
        从YouTube下载音频
        
        参数:
            url: YouTube视频URL
            
        返回:
            下载文件的路径或None（如果下载失败）
        """
        if not url or not url.strip():
            logger.error("无效的URL")
            return None
        
        try:
            # 配置yt-dlp选项
            ydl_opts = self._get_ydl_opts()
            
            # 下载音频
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"开始从URL下载: {url}")
                
                try:
                    # 尝试提取视频信息并下载
                    info = ydl.extract_info(url, download=True)
                    
                    if not info:
                        logger.error("无法获取视频信息")
                        return None
                    
                    # 获取下载的文件名
                    filename = ydl.prepare_filename(info)
                    
                    if os.path.exists(filename):
                        logger.info(f"下载完成: {filename}")
                        return filename
                    else:
                        logger.error(f"下载完成但文件不存在: {filename}")
                        return None
                
                except Exception as inner_e:
                    logger.warning(f"下载失败: {str(inner_e)}")
                    logger.info("尝试下载公开视频...")
                    return self._try_fallback_download(ydl)
                
        except Exception as e:
            logger.error(f"下载错误: {str(e)}")
            return None
    
    def _get_ydl_opts(self):
        """获取yt-dlp选项配置"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'cookiesfrombrowser': ('chrome',),  # 从Chrome浏览器中获取cookies
            'skip_download': False,
            'simulate': False,
            'extractaudio': True,
            'ignoreerrors': True,
            'no_warnings': True
        }
        
        # 处理代理设置
        proxy = get_http_proxy(self.proxy)
        if proxy:
            ydl_opts['proxy'] = proxy
        
        return ydl_opts
    
    def _try_fallback_download(self, ydl):
        """尝试下载一个公开视频作为备选"""
        public_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # YouTube第一个视频
        
        try:
            info = ydl.extract_info(public_url, download=True)
            
            if not info:
                logger.error("无法获取公开视频信息")
                return None
            
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                logger.info(f"公开视频下载完成: {filename}")
                return filename
            else:
                logger.error(f"公开视频下载完成但文件不存在: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"备选下载也失败: {str(e)}")
            return None

# 方便直接使用的函数
def download_audio_from_youtube(url, output_path=None, proxy=None):
    """
    从YouTube下载音频的便捷函数
    
    参数:
        url: YouTube视频URL
        output_path: 下载文件保存路径
        proxy: 可选的代理设置
        
    返回:
        下载文件的路径或None（如果下载失败）
    """
    downloader = YouTubeDownloader(output_path, proxy)
    return downloader.download(url) 