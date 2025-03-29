#!/usr/bin/env python3
"""
YouTube Audio Downloader
------------------------
A simple tool to download audio from YouTube videos in WebM format.
"""

import os
import sys
import yt_dlp
import logging
from typing import Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def download_audio(url: str, output_path: str = './downloads', proxy: str = None) -> Optional[str]:
    """
    从YouTube视频下载音频（保留原始WebM格式）
    
    参数:
        url (str): YouTube视频URL
        output_path (str): 保存下载音频的目录路径
        proxy (str): 可选的代理设置，格式如http://127.0.0.1:7890
    
    返回:
        Optional[str]: 下载文件的路径，失败时返回None
    """
    if not url or not url.strip():
        logger.error("无效的URL")
        return None
        
    try:
        # 创建输出目录（如果不存在）
        os.makedirs(output_path, exist_ok=True)
            
        # 配置yt-dlp选项 - 只下载最佳音频
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
        }
        
        # 如果提供了代理参数，使用传入的代理
        if proxy:
            logger.info(f"使用提供的代理: {proxy}")
            ydl_opts['proxy'] = proxy
        # 否则使用系统环境变量中的代理设置
        elif os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
            system_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            logger.info(f"使用系统代理: {system_proxy}")
            ydl_opts['proxy'] = system_proxy
        else:
            # 默认代理设置，仅作为备选
            default_proxy = 'http://127.0.0.1:63618'
            logger.info(f"未找到系统代理，使用默认代理: {default_proxy}")
            ydl_opts['proxy'] = default_proxy
        
        # 下载音频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"开始从URL下载: {url}")
            
            # 提取视频信息并下载
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
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"下载错误: {e}")
        return None
    except yt_dlp.utils.ExtractorError as e:
        logger.error(f"提取器错误: {e}")
        return None
    except Exception as e:
        logger.error(f"发生未知错误: {str(e)}")
        return None

def main():
    """主函数，处理命令行参数或使用默认URL"""
    # 从命令行获取URL或使用默认测试URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://www.youtube.com/watch?v=0k0MKpFI-JQ"
        logger.info(f"使用默认测试URL: {url}")
    
    # 下载音频
    result = download_audio(url)
    
    # 检查结果
    if result:
        print(f"\n成功下载到: {result}")
        return 0
    else:
        print("\n下载失败。请检查日志获取详细信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 