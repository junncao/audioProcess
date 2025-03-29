#!/usr/bin/env python3
"""
文件处理工具模块
-------------
提供文件读写和路径处理等功能
"""

import os
from pathlib import Path
from datetime import datetime

from audioprocess.utils.logger import get_logger
from audioprocess.config.settings import RESULTS_DIR

logger = get_logger(__name__)

def ensure_dir_exists(directory):
    """
    确保目录存在，如果不存在则创建
    
    参数:
        directory: 目录路径
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录时出错: {str(e)}")
        return False

def read_text_file(file_path):
    """
    读取文本文件内容
    
    参数:
        file_path: 文件路径
        
    返回:
        文件内容或None（如果读取失败）
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"成功读取文件: {file_path}")
        return content
        
    except Exception as e:
        logger.error(f"读取文件时出错: {str(e)}")
        return None

def write_text_file(file_path, content):
    """
    写入文本文件
    
    参数:
        file_path: 文件路径
        content: 要写入的内容
        
    返回:
        是否成功
    """
    try:
        # 确保父目录存在
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"成功写入文件: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"写入文件时出错: {str(e)}")
        return False

def generate_unique_filename(prefix, extension=".txt"):
    """
    生成唯一文件名
    
    参数:
        prefix: 文件名前缀
        extension: 文件扩展名，默认为 .txt
        
    返回:
        唯一文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}_{timestamp}{extension}"
    return filename

def generate_result_path(filename):
    """
    生成结果文件路径
    
    参数:
        filename: 文件名
        
    返回:
        结果文件的完整路径
    """
    return os.path.join(RESULTS_DIR, filename)

def save_result(content, prefix="result", extension=".txt", header=None):
    """
    保存结果到文件
    
    参数:
        content: 要保存的内容
        prefix: 文件名前缀，默认为 result
        extension: 文件扩展名，默认为 .txt
        header: 可选的文件头信息
        
    返回:
        保存的文件路径或None（如果保存失败）
    """
    try:
        # 生成唯一文件名
        filename = generate_unique_filename(prefix, extension)
        filepath = generate_result_path(filename)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            if header:
                f.write(f"{header}\n\n")
            f.write(content)
        
        logger.info(f"结果已保存到文件: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"保存结果时出错: {str(e)}")
        return None

def is_valid_audio_file(file_path):
    """
    检查是否为有效的音频文件
    
    参数:
        file_path: 文件路径
        
    返回:
        是否为有效的音频文件
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
            
        # 检查文件扩展名
        valid_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.webm']
        _, ext = os.path.splitext(file_path)
        
        if ext.lower() not in valid_extensions:
            logger.warning(f"文件扩展名 {ext} 不是常见的音频格式")
            return False
            
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"文件大小为0: {file_path}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"检查音频文件时出错: {str(e)}")
        return False 