#!/usr/bin/env python3
"""
语音转录模块
----------
使用阿里云 DashScope API 进行音频文件转录
"""

import os
import json
import requests
from http import HTTPStatus
from datetime import datetime

import dashscope
from dashscope.audio.asr import Transcription

from audioprocess.utils.logger import get_logger
from audioprocess.config.settings import DASHSCOPE_API_KEY, RESULTS_DIR

logger = get_logger(__name__)

class AudioTranscriber:
    """音频转录器类"""
    
    def __init__(self, api_key=None):
        """
        初始化转录器
        
        参数:
            api_key: DashScope API 密钥，默认使用配置中的密钥
        """
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", DASHSCOPE_API_KEY)
        dashscope.api_key = self.api_key
    
    def transcribe(self, file_url, language_hints=None):
        """
        转录音频文件
        
        参数:
            file_url: 音频文件URL
            language_hints: 语言提示，默认为['zh', 'en']
            
        返回:
            字典，包含转录文本和相关信息，如果转录失败则包含错误信息
        """
        try:
            logger.info(f"开始转录音频: {file_url}")
            
            # 设置语言提示，如果未提供则默认为中文和英文
            if language_hints is None:
                language_hints = ['zh', 'en']
            
            # 调用 DashScope API 进行异步转录
            task_response = Transcription.async_call(
                model='paraformer-v2',
                file_urls=[file_url],
                language_hints=language_hints
            )
            
            # 等待转录任务完成
            task_id = task_response.output.task_id
            logger.info(f"转录任务已提交，任务ID: {task_id}")
            transcribe_response = Transcription.wait(task=task_id)
            
            # 处理转录结果
            if transcribe_response.status_code == HTTPStatus.OK:
                logger.info("转录任务成功完成")
                return self._process_transcription_result(transcribe_response.output, file_url)
            else:
                logger.error(f"转录失败，状态码: {transcribe_response.status_code}")
                logger.error(f"错误信息: {transcribe_response.message}")
                return {
                    'error': f"转录请求失败: 状态码 {transcribe_response.status_code} - {transcribe_response.message}"
                }
                
        except Exception as e:
            logger.error(f"转录音频时出错: {str(e)}")
            return {
                'error': f"转录处理错误: {str(e)}"
            }
    
    def _process_transcription_result(self, transcription_result, file_url):
        """
        处理转录结果
        
        参数:
            transcription_result: DashScope转录结果
            file_url: 原始音频文件URL
            
        返回:
            处理后的结果字典
        """
        try:
            # 检查结果状态
            if transcription_result.get('task_status') == 'SUCCEEDED':
                # 从 results 中获取 transcription_url
                if 'results' in transcription_result and len(transcription_result['results']) > 0:
                    # 获取第一个结果的 transcription_url
                    transcription_url = transcription_result['results'][0].get('transcription_url')
                    
                    if transcription_url:
                        logger.info(f"找到 transcription_url: {transcription_url}")
                        
                        # 下载并解析转录JSON
                        transcription_json = self._download_json(transcription_url)
                        
                        # 从转录JSON中提取纯文本
                        text = self._extract_text_from_transcription(transcription_json)
                        
                        if text:
                            result = {'full_text': text, 'source_url': file_url}
                            
                            # 保存转录结果到本地文件
                            saved_file = self._save_transcription_result(text, file_url)
                            if saved_file:
                                result['saved_file'] = saved_file
                            
                            return result
                        else:
                            return {
                                'error': "无法从转录JSON中提取文本"
                            }
                    else:
                        logger.error("找不到 transcription_url")
                        return {
                            'error': "转录结果中找不到 transcription_url"
                        }
                else:
                    logger.error("找不到转录结果")
                    return {
                        'error': "转录结果中找不到 results 字段"
                    }
            elif transcription_result.get('task_status') == 'FAILED':
                # 处理失败情况
                error_code = transcription_result.get('code', '未知错误代码')
                error_message = transcription_result.get('message', '未知错误')
                logger.error(f"转录任务失败: {error_code} - {error_message}")
                
                # 检查是否有具体的失败细节
                if 'results' in transcription_result:
                    for result in transcription_result['results']:
                        if result.get('subtask_status') == 'FAILED':
                            sub_error_code = result.get('code', '未知错误代码')
                            sub_error_message = result.get('message', '未知错误')
                            logger.error(f"子任务失败: {sub_error_code} - {sub_error_message}")
                            return {
                                'error': f"转录失败: {sub_error_code} - {sub_error_message}"
                            }
                
                return {
                    'error': f"转录任务失败: {error_code} - {error_message}"
                }
            else:
                logger.warning(f"未知的任务状态: {transcription_result.get('task_status')}")
                return {
                    'error': f"未知的任务状态: {transcription_result.get('task_status')}"
                }
        
        except Exception as parse_error:
            logger.error(f"解析转录结果时出错: {str(parse_error)}")
            return {
                'error': f"解析转录结果时出错: {str(parse_error)}"
            }
    
    def _download_json(self, url):
        """
        下载并解析JSON URL
        
        参数:
            url: JSON文件的URL
            
        返回:
            解析后的JSON对象或None（如果下载失败）
        """
        try:
            logger.info(f"从URL下载JSON: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 解析JSON内容
            json_data = response.json()
            logger.info("JSON下载并解析成功")
            return json_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"下载JSON时出错: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON时出错: {str(e)}")
            return None
    
    def _extract_text_from_transcription(self, json_data):
        """
        从转录JSON中提取纯文本
        
        参数:
            json_data: 转录JSON数据
            
        返回:
            提取的纯文本或None（如果提取失败）
        """
        try:
            if not json_data:
                return None
                
            # 查找transcripts字段
            if 'transcripts' in json_data and len(json_data['transcripts']) > 0:
                # 提取文本
                full_text = json_data['transcripts'][0]['text']
                logger.info("成功从转录JSON提取文本内容")
                return full_text
            else:
                logger.error("转录JSON中未找到文本内容")
                return None
                
        except Exception as e:
            logger.error(f"从转录JSON提取文本时出错: {str(e)}")
            return None
    
    def _save_transcription_result(self, text, source_url):
        """
        将转录文本保存到本地文件
        
        参数:
            text: 转录的文本内容
            source_url: 源音频URL
            
        返回:
            保存的文件路径
        """
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 创建文件名
            filename = f"transcription_{timestamp}.txt"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                if source_url:
                    f.write(f"音频来源: {source_url}\n\n")
                
                f.write("==== 转录文本 ====\n\n")
                f.write(text)
            
            logger.info(f"转录结果已保存到文件: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存转录结果时出错: {str(e)}")
            return None

# 方便直接使用的函数
def transcribe_audio(file_url, language_hints=None):
    """
    转录音频文件的便捷函数
    
    参数:
        file_url: 音频文件URL
        language_hints: 语言提示，默认为['zh', 'en']
        
    返回:
        字典，包含转录文本和相关信息，如果转录失败则包含错误信息
    """
    transcriber = AudioTranscriber()
    return transcriber.transcribe(file_url, language_hints) 