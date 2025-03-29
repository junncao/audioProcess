#!/usr/bin/env python3
"""
文本摘要模块
----------
使用阿里云 DashScope 的 Qwen 模型对文本内容进行摘要
"""

import os
from datetime import datetime
from openai import OpenAI

from audioprocess.utils.logger import get_logger
from audioprocess.utils.proxy_manager import no_proxy_context
from audioprocess.config.settings import (
    DASHSCOPE_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    SUMMARY_SYSTEM_PROMPT,
    RESULTS_DIR
)

logger = get_logger(__name__)

class TextSummarizer:
    """文本摘要器类"""
    
    def __init__(self, api_key=None, base_url=None, model=None):
        """
        初始化摘要器
        
        参数:
            api_key: DashScope API 密钥，默认使用配置中的密钥
            base_url: OpenAI 兼容 API 基础 URL，默认使用配置中的 URL
            model: 使用的模型名称，默认使用配置中的模型
        """
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", DASHSCOPE_API_KEY)
        self.base_url = base_url or OPENAI_BASE_URL
        self.model = model or OPENAI_MODEL
    
    def summarize(self, text, disable_proxy=True):
        """
        对文本进行摘要
        
        参数:
            text: 需要摘要的文本内容
            disable_proxy: 是否禁用代理进行请求，默认为 True
            
        返回:
            摘要文本或错误消息（如果摘要失败）
        """
        if not text:
            logger.error("无文本内容可供摘要")
            return "摘要生成失败: 无文本内容"
        
        try:
            logger.info("开始使用 Qwen 大模型进行文本摘要...")
            
            # 构建提示词，要求模型进行文本摘要
            system_prompt = SUMMARY_SYSTEM_PROMPT
            user_prompt = f"请总结以下文本内容：\n\n{text}"
            
            # 确定是否需要禁用代理
            if disable_proxy:
                # 使用代理上下文管理器禁用代理
                with no_proxy_context():
                    return self._call_api(system_prompt, user_prompt)
            else:
                # 不改变代理设置
                return self._call_api(system_prompt, user_prompt)
            
        except Exception as e:
            logger.error(f"生成文本摘要时出错: {str(e)}")
            return f"摘要生成失败: {str(e)}"
    
    def _call_api(self, system_prompt, user_prompt):
        """
        调用 API 生成摘要
        
        参数:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        返回:
            摘要文本或错误消息
        """
        try:
            # 创建 OpenAI 客户端配置
            client_kwargs = {
                'api_key': self.api_key,
                'base_url': self.base_url,
            }
            
            # 初始化 OpenAI 客户端
            client = OpenAI(**client_kwargs)
            
            # 调用模型进行文本摘要
            logger.info("发送API请求到DashScope...")
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                timeout=60  # 设置60秒超时
            )
            
            # 提取摘要文本
            summary = completion.choices[0].message.content
            
            logger.info("文本摘要生成成功")
            
            # 返回摘要文本
            return summary
            
        except Exception as api_error:
            # 特别处理 SOCKS 代理错误
            error_str = str(api_error)
            if "SOCKS proxy" in error_str and "socksio" in error_str:
                logger.error("检测到SOCKS代理错误，但缺少必要的支持库")
                logger.error("解决方法: pip install httpx[socks] 或使用 --no-proxy 参数")
                return "摘要生成失败: SOCKS代理错误，请安装'httpx[socks]'或使用--no-proxy参数"
            else:
                # 其他 API 错误
                logger.error(f"API调用失败: {error_str}")
                return f"摘要生成失败: API调用错误: {error_str}"
    
    def save_summary(self, text, summary, source_info=None):
        """
        保存原文本和摘要到文件
        
        参数:
            text: 原始文本
            summary: 摘要文本
            source_info: 来源信息（可选）
            
        返回:
            保存的文件路径或None（如果保存失败）
        """
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 创建文件名
            filename = f"summary_{timestamp}.txt"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                if source_info:
                    f.write(f"来源: {source_info}\n\n")
                
                f.write("==== 原文内容 ====\n\n")
                f.write(text)
                f.write("\n\n")
                
                f.write("==== 文本摘要 ====\n\n")
                f.write(summary)
            
            logger.info(f"摘要结果已保存到文件: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存摘要结果时出错: {str(e)}")
            return None

# 方便直接使用的函数
def summarize_text(text, disable_proxy=True):
    """
    对文本进行摘要的便捷函数
    
    参数:
        text: 需要摘要的文本内容
        disable_proxy: 是否禁用代理进行请求，默认为 True
        
    返回:
        摘要文本或错误消息（如果摘要失败）
    """
    summarizer = TextSummarizer()
    return summarizer.summarize(text, disable_proxy)

def save_summary_result(text, summary, source_info=None):
    """
    保存原文本和摘要到文件的便捷函数
    
    参数:
        text: 原始文本
        summary: 摘要文本
        source_info: 来源信息（可选）
        
    返回:
        保存的文件路径或None（如果保存失败）
    """
    summarizer = TextSummarizer()
    return summarizer.save_summary(text, summary, source_info) 