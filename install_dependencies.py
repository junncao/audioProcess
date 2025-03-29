#!/usr/bin/env python3
"""
依赖安装脚本
-----------
安装项目所需的所有依赖，包括对SOCKS代理的支持
"""

import os
import sys
import subprocess
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_command(command):
    """运行命令并返回结果"""
    logger.info(f"执行命令: {command}")
    process = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if process.returncode != 0:
        logger.error(f"命令执行失败，退出码: {process.returncode}")
        logger.error(f"错误信息: {process.stderr}")
        return False
    return True

def main():
    """主函数 - 安装所有依赖"""
    logger.info("开始安装项目依赖...")
    
    # 项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(script_dir, "requirements.txt")
    
    # 检查requirements.txt是否存在
    if not os.path.exists(requirements_file):
        logger.error(f"依赖文件不存在: {requirements_file}")
        return 1
    
    # 1. 更新pip
    logger.info("更新pip...")
    if not run_command(f"{sys.executable} -m pip install --upgrade pip"):
        logger.warning("pip更新失败，继续安装依赖...")
    
    # 2. 安装基本依赖
    logger.info("安装基本依赖...")
    if not run_command(f"{sys.executable} -m pip install -r {requirements_file}"):
        logger.error("基本依赖安装失败")
        return 1
    
    # 3. 确保SOCKS代理支持已安装
    logger.info("安装SOCKS代理支持...")
    if not run_command(f"{sys.executable} -m pip install httpx[socks]"):
        logger.error("SOCKS代理支持安装失败")
        logger.info("尝试单独安装socksio...")
        if not run_command(f"{sys.executable} -m pip install socksio"):
            logger.error("socksio安装失败")
            return 1
    
    logger.info("所有依赖安装成功！")
    logger.info("\n使用方法示例:")
    logger.info("1. 运行完整流程: python main.py --url https://www.youtube.com/watch?v=示例ID")
    logger.info("2. 仅测试摘要: python tests/test_summarize.py --text \"测试文本\"")
    logger.info("3. 禁用代理: python main.py --url https://www.youtube.com/watch?v=示例ID --no-proxy")
    logger.info("4. 为YouTube指定代理: python main.py --url https://www.youtube.com/watch?v=示例ID --youtube-proxy http://127.0.0.1:7890")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 