#!/usr/bin/env python3
"""
日志工具模块
-----------
提供统一的日志配置和管理
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from audioprocess.config.settings import LOG_FORMAT, LOG_DATE_FORMAT, ROOT_DIR

# 日志级别映射
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

def setup_logger(name='audioprocess', level='info', log_file=None, console=True):
    """
    设置日志记录器
    
    参数:
        name: 日志记录器名称
        level: 日志级别 ('debug', 'info', 'warning', 'error', 'critical')
        log_file: 日志文件路径，如果为None则不记录到文件
        console: 是否输出到控制台
        
    返回:
        配置好的日志记录器对象
    """
    logger = logging.getLogger(name)
    
    # 设置日志级别
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    logger.setLevel(log_level)
    
    # 清除现有的处理程序
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建格式化程序
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # 添加控制台处理程序
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 添加文件处理程序
    if log_file:
        log_dir = Path(ROOT_DIR) / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        if not Path(log_file).is_absolute():
            log_file = log_dir / log_file
            
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 创建默认应用日志记录器
app_logger = setup_logger('audioprocess')

def get_logger(name=None):
    """
    获取指定名称的日志记录器，如果未指定则返回应用默认日志记录器
    
    参数:
        name: 日志记录器名称，可以是子模块名称，如'audioprocess.core'
        
    返回:
        日志记录器对象
    """
    if name:
        return logging.getLogger(name)
    return app_logger 