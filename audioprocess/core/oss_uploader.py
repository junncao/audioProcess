#!/usr/bin/env python3
"""
阿里云 OSS 上传模块
----------------
提供将文件上传到阿里云 OSS 的功能
"""

import os
import random
import string
from datetime import datetime
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider

from audioprocess.utils.logger import get_logger
from audioprocess.config.settings import (
    OSS_ENDPOINT, 
    OSS_REGION, 
    OSS_BUCKET_NAME, 
    OSS_ACCESS_KEY_ID, 
    OSS_ACCESS_KEY_SECRET
)

logger = get_logger(__name__)

class OssUploader:
    """阿里云OSS上传器类"""
    
    def __init__(self, bucket_name=None, endpoint=None, region=None, access_key_id=None, access_key_secret=None):
        """
        初始化上传器
        
        参数:
            bucket_name: OSS存储桶名称，默认使用配置中的存储桶
            endpoint: OSS终端节点，默认使用配置中的终端节点
            region: OSS区域，默认使用配置中的区域
            access_key_id: 访问密钥ID，默认使用配置中的密钥ID
            access_key_secret: 访问密钥密码，默认使用配置中的密钥密码
        """
        self.bucket_name = bucket_name or OSS_BUCKET_NAME
        self.endpoint = endpoint or OSS_ENDPOINT
        self.region = region or OSS_REGION
        self.access_key_id = access_key_id or OSS_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or OSS_ACCESS_KEY_SECRET
        
        # 初始化OSS客户端
        self.bucket = self._init_bucket()
    
    def upload(self, file_path):
        """
        上传文件到OSS
        
        参数:
            file_path: 本地文件路径
            
        返回:
            上传文件的签名URL或None（如果上传失败）
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            # 生成唯一的对象名
            object_name = self._generate_object_name(file_path)
            
            # 上传文件
            logger.info(f"开始上传文件到OSS: {object_name}")
            with open(file_path, 'rb') as file_obj:
                result = self.bucket.put_object(object_name, file_obj)
            
            if result.status == 200:
                logger.info(f"文件上传成功，状态码: {result.status}")
                
                # 生成带签名的临时URL（有效期24小时）
                file_url = self.bucket.sign_url('GET', object_name, 60 * 60 * 24)
                logger.info(f"已生成带签名的临时URL，有效期24小时")
                
                # 也记录不带签名的URL（仅用于显示和记录）
                public_url = f"https://{self.bucket_name}.{self.endpoint.replace('https://', '')}/{object_name}"
                logger.info(f"公共URL（需要适当的存储桶权限才能访问）: {public_url}")
                
                return file_url
            else:
                logger.error(f"文件上传失败，状态码: {result.status}")
                return None
        
        except Exception as e:
            logger.error(f"上传文件到OSS时出错: {str(e)}")
            return None
    
    def _init_bucket(self):
        """
        初始化OSS Bucket
        
        返回:
            OSS Bucket对象
        """
        try:
            # 首先尝试使用环境变量中的凭证
            if 'OSS_ACCESS_KEY_ID' in os.environ and 'OSS_ACCESS_KEY_SECRET' in os.environ:
                logger.info("使用环境变量中的OSS凭证")
                auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())
                bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name, region=self.region)
            else:
                # 使用实例中定义的凭证
                logger.info("使用实例中定义的OSS凭证")
                auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            
            return bucket
            
        except Exception as e:
            logger.error(f"初始化OSS客户端时出错: {str(e)}")
            raise
    
    def _generate_object_name(self, file_path):
        """
        生成唯一的对象名
        
        参数:
            file_path: 原始文件路径
            
        返回:
            生成的对象名
        """
        # 使用时间戳和随机数生成纯英文文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 生成随机字符串作为前缀
        random_prefix = ''.join(random.choices(string.ascii_lowercase, k=8))
        
        # 保留原始扩展名
        _, ext = os.path.splitext(file_path)
        # 确保扩展名是小写英文字母
        ext = ext.lower()
        
        # 构建纯英文文件名
        return f"audio_{random_prefix}_{timestamp}{ext}"

# 方便直接使用的函数
def upload_file_to_oss(file_path):
    """
    上传文件到阿里云OSS的便捷函数
    
    参数:
        file_path: 本地文件路径
        
    返回:
        上传文件的签名URL或None（如果上传失败）
    """
    uploader = OssUploader()
    return uploader.upload(file_path) 