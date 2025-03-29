#!/usr/bin/env python3
"""
代理管理工具
-----------
管理代理设置和环境变量
"""

import os
import contextlib
from audioprocess.utils.logger import get_logger

logger = get_logger(__name__)

def check_socks_dependency():
    """
    检查是否存在SOCKS代理并且缺少socksio包
    
    返回:
        bool: 如果缺少socksio包但使用了SOCKS代理则返回False，否则返回True
    """
    # 查找系统中所有可能的代理环境变量
    proxy_vars = ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    socks_found = False
    
    # 检查是否有代理环境变量中使用了SOCKS
    for var in proxy_vars:
        if var in os.environ and 'socks' in os.environ[var].lower():
            socks_found = True
            break
    
    # 如果使用了SOCKS代理，检查是否安装了socksio
    if socks_found:
        try:
            import socksio
            logger.info("检测到SOCKS代理，socksio已安装，可以正常使用")
            return True
        except ImportError:
            return False
            
    return True

def get_http_proxy(custom_proxy=None):
    """
    获取HTTP代理设置
    
    参数:
        custom_proxy: 自定义代理地址，优先使用
        
    返回:
        str: 代理地址或None
    """
    from audioprocess.config.settings import DEFAULT_PROXY
    
    if custom_proxy:
        logger.info(f"使用提供的自定义代理: {custom_proxy}")
        return custom_proxy
    
    # 检查环境变量
    for var in ['HTTP_PROXY', 'http_proxy']:
        if var in os.environ and os.environ[var]:
            logger.info(f"使用系统环境变量中的代理: {os.environ[var]}")
            return os.environ[var]
    
    # 使用默认代理
    logger.info(f"未找到系统代理，使用默认代理: {DEFAULT_PROXY}")
    return DEFAULT_PROXY

def disable_all_proxies():
    """
    禁用所有代理设置
    """
    logger.info("禁用所有代理设置")
    
    # 清除所有代理环境变量
    for var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if var in os.environ:
            del os.environ[var]
    
    # 设置NO_PROXY环境变量
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'

@contextlib.contextmanager
def no_proxy_context():
    """
    临时禁用所有代理的上下文管理器
    
    使用示例:
    ```
    with no_proxy_context():
        # 在这里的代码将在无代理环境中运行
        response = requests.get('https://example.com')
    # 离开上下文后，原有的代理设置会被恢复
    ```
    """
    # 保存原始代理设置
    original_proxies = {}
    for var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']:
        if var in os.environ:
            original_proxies[var] = os.environ[var]
    
    try:
        # 禁用所有代理
        disable_all_proxies()
        logger.info("临时禁用所有代理")
        yield
    finally:
        # 恢复原始代理设置
        for var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']:
            if var in os.environ:
                del os.environ[var]
                
        for var, value in original_proxies.items():
            os.environ[var] = value
            
        logger.info("已恢复原始代理设置") 