#!/usr/bin/env python3
"""
setup.py - AudioProcess
-------------------
为AudioProcess包创建安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="audioprocess",
    version="1.0.0",
    description="一个用于从YouTube下载音频，上传到阿里云OSS，并使用DashScope进行转录和摘要的工具包",
    author="CC",
    packages=find_packages(),
    install_requires=[
        "yt-dlp>=2023.3.4",
        "oss2>=2.17.0",
        "dashscope>=1.10.0",
        "requests>=2.28.2",
        "openai>=1.3.0",
    ],
    entry_points={
        'console_scripts': [
            'audioprocess=audioprocess.main:main',
        ],
    },
    python_requires=">=3.8",
) 