#!/usr/bin/env python3
"""
YouTube 音频下载并上传到阿里云 OSS
-----------------------------------
根据 YouTube URL 下载音频，然后上传到阿里云 OSS 存储，并返回访问 URL
最后使用阿里云 DashScope API 进行语音识别和文本摘要

增加功能：先检查YouTube视频是否自带字幕，如有则直接提取字幕内容进行总结
"""

import os
import sys
import logging
import json
from datetime import datetime
from http import HTTPStatus
import yt_dlp
import oss2
import requests
from oss2.credentials import EnvironmentVariableCredentialsProvider
import dashscope
from dashscope.audio.asr import Transcription
import argparse
from openai import OpenAI
from audioprocess.config.settings import (
    OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, DASHSCOPE_API_KEY,
    OSS_BUCKET_NAME, OSS_ENDPOINT, OSS_REGION
)# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 检查SOCKS代理设置函数定义保留，但不在启动时调用
def check_socks_dependency():
    """检查是否存在SOCKS代理并且缺少socksio包"""
    # 查找系统中所有可能的代理环境变量
    proxy_vars = ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    socks_found = False
    
    for var in proxy_vars:
        if var in os.environ and 'socks' in os.environ[var].lower():
            socks_found = True
            break
    
    if socks_found:
        try:
            # 尝试导入socksio包
            import socksio
            logger.info("检测到SOCKS代理，socksio已安装，可以正常使用")
            return True
        except ImportError:
            logger.warning("""
========================================================================
警告: 检测到系统使用SOCKS代理，但缺少必要的支持库!
这可能导致摘要功能失败。您有以下选择:

1. 安装所需依赖: pip install httpx[socks]
2. 运行安装脚本: python install_dependencies.py
3. 禁用代理运行: python main.py --no-proxy ...其他参数
========================================================================
            """)
            return False
    return True

# 创建用于保存转录和摘要结果的文件夹
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcription_results")
os.makedirs(RESULTS_DIR, exist_ok=True)


# DashScope 配置
dashscope.api_key = DASHSCOPE_API_KEY

def download_audio_from_youtube(url, output_path='./downloads', proxy=None):
    """
    从 YouTube 下载音频
    
    参数:
        url: YouTube 视频 URL
        output_path: 下载文件保存路径
        proxy: 可选的代理设置，格式如http://127.0.0.1:7890
        
    返回:
        下载文件的路径或 None（如果下载失败）
    """
    if not url or not url.strip():
        logger.error("无效的 URL")
        return None
        
    try:
        # 创建输出目录（如果不存在）
        os.makedirs(output_path, exist_ok=True)
            
        # 配置 yt-dlp 选项
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'cookiesfrombrowser': ('chrome',),  # 从 Chrome 浏览器中获取 cookies
            # 其他可选项: 'firefox', 'opera', 'edge', 'chromium', 'brave', 'vivaldi', 'safari'
            # 如果需要指定浏览器配置文件路径: ('chrome', 'cookies', '/path/to/profile')
            'skip_download': False,  # 是否跳过下载
            'simulate': False,       # 是否只模拟下载
            'extractaudio': True,    # 提取音频
            'ignoreerrors': True,    # 忽略错误
            'no_warnings': True      # 禁用警告
        }
        
        # 处理代理设置
        if proxy:
            logger.info(f"使用提供的代理: {proxy}")
            ydl_opts['proxy'] = proxy
        elif os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
            system_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            logger.info(f"使用系统代理: {system_proxy}")
            ydl_opts['proxy'] = system_proxy
        else:
            default_proxy = 'http://127.0.0.1:63618'
            logger.info(f"未找到系统代理，使用默认代理: {default_proxy}")
            ydl_opts['proxy'] = default_proxy
        
        # 下载音频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"开始从 URL 下载: {url}")
            
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
                logger.warning(f"使用 cookies 下载失败: {str(inner_e)}")
                logger.info("尝试下载公开视频...")
                
                # 设置不需要 cookies 的公开 URL
                public_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # YouTube 第一个视频
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
        logger.error(f"下载错误: {str(e)}")
        return None

def upload_file_to_oss(file_path):
    """
    将文件上传到阿里云 OSS
    
    参数:
        file_path: 本地文件路径
        
    返回:
        上传文件的访问 URL 或 None（如果上传失败）
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None, None
        
    try:
        # 获取阿里云凭证 - 首先尝试使用环境变量，如果不存在则使用代码中定义的密钥
        if 'OSS_ACCESS_KEY_ID' in os.environ and 'OSS_ACCESS_KEY_SECRET' in os.environ:
            # 使用环境变量中的凭证
            logger.info("使用环境变量中的 OSS 凭证")
            auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())
            bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME, region=OSS_REGION)
        else:
            # 使用代码中定义的凭证
            logger.info("使用代码中定义的 OSS 凭证")
            # 创建普通认证对象
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
            # 创建 Bucket 对象时不需要传递 region 参数
            bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
        
        # 使用时间戳和随机数生成纯英文文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import random
        import string
        # 生成随机字符串作为前缀
        random_prefix = ''.join(random.choices(string.ascii_lowercase, k=8))
        
        # 保留原始扩展名
        _, ext = os.path.splitext(file_path)
        # 确保扩展名是小写英文字母
        ext = ext.lower()
        
        # 构建纯英文文件名
        object_name = f"audio_{random_prefix}_{timestamp}{ext}"
        
        # 上传文件
        logger.info(f"开始上传文件到 OSS: {object_name}")
        with open(file_path, 'rb') as file_obj:
            result = bucket.put_object(object_name, file_obj)
            
        if result.status == 200:
            logger.info(f"文件上传成功，状态码: {result.status}")
            
            # 生成带签名的临时 URL (有效期 24 小时)
            file_url = bucket.sign_url('GET', object_name, 60 * 60 * 24)
            logger.info(f"已生成带签名的临时 URL，有效期 24 小时")
            
            # 也记录不带签名的 URL (仅用于显示和记录)
            public_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT.replace('https://', '')}/{object_name}"
            logger.info(f"公共 URL (需要适当的存储桶权限才能访问): {public_url}")
            
            return file_url, object_name
        else:
            logger.error(f"文件上传失败，状态码: {result.status}")
            return None, None
            
    except Exception as e:
        logger.error(f"上传文件到 OSS 时出错: {str(e)}")
        return None, None

def download_json(url):
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

def extract_text_from_transcription(json_data):
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

def summarize_text(text):
    """
    使用阿里云 DashScope 的 Qwen 大模型对文本进行摘要总结
    
    参数:
        text: 需要总结的文本内容
        
    返回:
        摘要文本或错误信息（如果总结失败）
    """
    if not text:
        logger.error("无文本内容可供摘要")
        return None
        
    try:
        logger.info("开始使用 Qwen 大模型进行文本摘要...")
        
        # 使用环境变量中的DashScope API Key，或者直接使用之前的API Key
        api_key = os.getenv("DASHSCOPE_API_KEY", dashscope.api_key)
        
        # 保存原始代理设置
        original_proxies = {}
        for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'NO_PROXY', 'no_proxy']:
            if proxy_var in os.environ:
                original_proxies[proxy_var] = os.environ[proxy_var]
        
        # 彻底清除所有代理设置
        for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
        
        # 明确禁用所有代理
        os.environ['NO_PROXY'] = '*'
        os.environ['no_proxy'] = '*'
        
        logger.info("摘要处理过程中已临时禁用所有代理")
        
        try:
            # 创建OpenAI客户端配置
            client_kwargs = {
                'api_key': api_key,
                'base_url': "https://dashscope.aliyuncs.com/compatible-mode/v1",
            }
            
            # 初始化OpenAI客户端
            client = OpenAI(**client_kwargs)
            
            # 构建提示词，要求模型进行文本摘要
            system_prompt = "你是一个专业的内容摘要助手。请简明扼要地总结以下内容的要点，保留所有信息但是更简洁。如果总结后的语言是英文，翻译成中文再发给我"
            user_prompt = f"请总结以下文本内容：\n\n{text}"
            
            # 调用模型进行文本摘要
            logger.info("发送API请求到DashScope...")
            try:
                completion = client.chat.completions.create(
                    model="qwen-plus",  # 使用qwen-plus模型
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
                # 特别处理SOCKS代理错误
                error_str = str(api_error)
                if "SOCKS proxy" in error_str and "socksio" in error_str:
                    # 当实际发生SOCKS代理错误时才检查并显示提示
                    logger.error("检测到SOCKS代理错误，但缺少必要的支持库")
                    logger.error("解决方法: pip install httpx[socks] 或使用 --no-proxy 参数")
                    return "摘要生成失败: SOCKS代理错误，请安装'httpx[socks]'或使用--no-proxy参数"
                else:
                    # 其他API错误
                    logger.error(f"API调用失败: {error_str}")
                    return f"摘要生成失败: API调用错误: {error_str}"
            
        finally:
            # 恢复原始代理设置
            for proxy_var, value in original_proxies.items():
                os.environ[proxy_var] = value
            
            logger.info("已恢复原始代理设置")
        
    except Exception as e:
        logger.error(f"生成文本摘要时出错: {str(e)}")
        return f"摘要生成失败: {str(e)}"

def save_transcription_result(text, summary=None, source_url=None, prefix="transcription"):
    """
    将转录文本和摘要保存到本地文件
    
    参数:
        text: 转录的文本内容
        summary: 文本摘要（如果有）
        source_url: 源音频URL（如果有）
        prefix: 文件名前缀
        
    返回:
        保存的文件路径
    """
    try:
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 创建文件名
        filename = f"{prefix}_{timestamp}.txt"
        filepath = os.path.join(RESULTS_DIR, filename)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            if source_url:
                f.write(f"音频来源: {source_url}\n\n")
            
            f.write("==== 转录文本 ====\n\n")
            f.write(text)
            f.write("\n\n")
            
            if summary:
                f.write("==== 文本摘要 ====\n\n")
                f.write(summary)
        
        logger.info(f"转录结果已保存到文件: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"保存转录结果时出错: {str(e)}")
        return None

def transcribe_audio(file_url, skip_summary=False):
    """
    使用阿里云 DashScope 语音识别服务转录音频
    
    参数:
        file_url: 音频文件的 OSS URL
        skip_summary: 是否跳过生成文本摘要
        
    返回:
        转录的文本和摘要（如果转录成功），或错误信息（如果转录失败）
    """
    try:
        logger.info(f"开始转录音频: {file_url}")
        
        # 调用 DashScope API 进行异步转录
        task_response = Transcription.async_call(
            model='paraformer-v2',
            file_urls=[file_url],
            language_hints=['zh', 'en']  # 支持中文和英文
        )
        
        # 等待转录任务完成
        logger.info(f"转录任务已提交，任务ID: {task_response.output.task_id}")
        transcribe_response = Transcription.wait(task=task_response.output.task_id)
        
        # 处理转录结果
        if transcribe_response.status_code == HTTPStatus.OK:
            logger.info("转录任务成功完成")
            
            # 提取转录文本
            transcription_result = transcribe_response.output
            # 保存转录原始JSON结果
            # result_file = os.path.join(RESULTS_DIR, f"transcription_raw_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
            # with open(result_file, 'w', encoding='utf-8') as f:
            #     json.dump(transcription_result, f, ensure_ascii=False, indent=4)
                
            # logger.info(f"转录原始结果已保存到文件: {result_file}")
            
            # 处理多层结构的JSON结果
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
                            transcription_json = download_json(transcription_url)
                            
                            # 从转录JSON中提取纯文本
                            text = extract_text_from_transcription(transcription_json)
                            
                            if text:
                                result = {'full_text': text}
                                
                                # 生成文本摘要（除非指定跳过）
                                summary = None
                                if not skip_summary:
                                    logger.info("转录成功，开始生成文本摘要...")
                                    # 彻底清除可能的SOCKS代理设置，避免摘要生成失败
                                    original_proxies = {}
                                    for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                                        if proxy_var in os.environ:
                                            original_proxies[proxy_var] = os.environ.get(proxy_var)
                                            del os.environ[proxy_var]
                                    # 明确禁用所有代理
                                    os.environ['NO_PROXY'] = '*'
                                    
                                    try:
                                        # 调用摘要函数
                                        summary = summarize_text(text)
                                        if summary and not summary.startswith("摘要生成失败"):
                                            result['summary'] = summary
                                        else:
                                            # 摘要失败但不影响整体流程
                                            logger.warning(f"摘要生成失败，但转录结果有效: {summary}")
                                    finally:
                                        # 恢复原始代理设置
                                        for proxy_var, value in original_proxies.items():
                                            if value is not None:
                                                os.environ[proxy_var] = value
                                else:
                                    logger.info("按要求跳过文本摘要步骤")
                                
                                # 保存转录和摘要结果到本地文件
                                saved_file = save_transcription_result(text, summary, file_url)
                                if saved_file:
                                    result['saved_file'] = saved_file
                                
                                # 返回转录文本和可能的摘要
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
                # 返回错误信息
                return {
                    'error': f"解析转录结果时出错: {str(parse_error)}"
                }
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

def extract_youtube_subtitles(url, proxy=None):
    """
    从YouTube视频中提取字幕（优先中文，其次英文）
    
    参数:
        url: YouTube视频URL
        proxy: 可选的代理设置
        
    返回:
        字典，包含提取到的字幕文本和语言信息，如果没有字幕则返回None
    """
    if not url or not url.strip():
        logger.error("无效的URL")
        return None
    
    try:
        logger.info(f"尝试从视频中提取字幕: {url}")
        
        # 配置yt-dlp选项 - 只获取字幕信息，不下载视频
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh-Hans', 'zh-CN', 'zh', 'en'],  # 优先中文，其次英文
            'subtitlesformat': 'best',
            'quiet': False,
            'no_warnings': False,
            'cookiesfrombrowser': ('chrome',),
        }
        
        # 处理代理设置
        if proxy:
            logger.info(f"使用提供的代理: {proxy}")
            ydl_opts['proxy'] = proxy
        elif os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy'):
            system_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            logger.info(f"使用系统代理: {system_proxy}")
            ydl_opts['proxy'] = system_proxy
        else:
            default_proxy = 'http://127.0.0.1:63618'
            logger.info(f"未找到系统代理，使用默认代理: {default_proxy}")
            ydl_opts['proxy'] = default_proxy
        
        # 创建临时目录存放字幕文件
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_subtitles")
        os.makedirs(temp_dir, exist_ok=True)
        ydl_opts['paths'] = {'home': temp_dir}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 提取视频信息，包括字幕
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.error("无法获取视频信息")
                return None
            
            # 检查是否有字幕可用
            if not info.get('subtitles') and not info.get('automatic_captions'):
                logger.info("该视频没有可用的字幕（手动或自动）")
                return None
            
            # 优先使用手动添加的字幕，其次使用自动生成的字幕
            subtitles_dict = info.get('subtitles', {}) or info.get('automatic_captions', {})
            
            if not subtitles_dict:
                logger.info("未找到任何字幕")
                return None
            
            # 按优先级查找字幕语言
            preferred_langs = ['zh-Hans', 'zh-CN', 'zh', 'en']
            selected_lang = None
            
            for lang in preferred_langs:
                if lang in subtitles_dict and subtitles_dict[lang]:
                    selected_lang = lang
                    break
            
            if not selected_lang:
                # 如果没有找到首选语言，使用第一个可用的语言
                available_langs = list(subtitles_dict.keys())
                if available_langs:
                    selected_lang = available_langs[0]
                else:
                    logger.info("未找到任何字幕语言")
                    return None
            
            # 获取字幕下载链接
            logger.info(f"找到字幕，语言: {selected_lang}")
            subtitle_formats = subtitles_dict[selected_lang]
            
            # 优先选择文本格式的字幕
            preferred_formats = ['vtt', 'ttml', 'srv3', 'srv2', 'srv1', 'json3']
            selected_format = None
            subtitle_url = None
            
            for fmt in preferred_formats:
                for subtitle in subtitle_formats:
                    if subtitle.get('ext') == fmt:
                        selected_format = fmt
                        subtitle_url = subtitle.get('url')
                        break
                if selected_format:
                    break
            
            if not subtitle_url:
                # 如果没有找到首选格式，使用第一个可用的格式
                if subtitle_formats and 'url' in subtitle_formats[0]:
                    subtitle_url = subtitle_formats[0]['url']
                    selected_format = subtitle_formats[0].get('ext', 'unknown')
                else:
                    logger.error("无法获取字幕下载链接")
                    return None
            
            # 下载字幕
            logger.info(f"开始下载{selected_format}格式的{selected_lang}字幕...")
            try:
                response = requests.get(subtitle_url, timeout=30)
                response.raise_for_status()
                subtitle_content = response.text
                
                # 解析不同格式的字幕内容
                if selected_format == 'json3':
                    # 解析JSON格式字幕
                    try:
                        json_data = json.loads(subtitle_content)
                        events = json_data.get('events', [])
                        subtitle_text = ""
                        
                        for event in events:
                            if 'segs' in event:
                                for seg in event['segs']:
                                    if 'utf8' in seg:
                                        subtitle_text += seg['utf8'] + " "
                        
                        subtitle_text = subtitle_text.strip()
                    except Exception as e:
                        logger.error(f"解析JSON字幕失败: {str(e)}")
                        return None
                else:
                    # 使用简单方法提取文本（适用于VTT、SRT等格式）
                    # 这里的实现较为简单，可能需要更复杂的解析器来完全解析不同的字幕格式
                    lines = subtitle_content.split('\n')
                    subtitle_text = ""
                    
                    for line in lines:
                        # 跳过时间戳和元数据行
                        if '-->' in line or line.strip().isdigit() or not line.strip():
                            continue
                        # 跳过WebVTT头部
                        if 'WEBVTT' in line:
                            continue
                        # 保留文本内容
                        subtitle_text += line.strip() + " "
                    
                    subtitle_text = subtitle_text.strip()
                
                if not subtitle_text:
                    logger.error("提取的字幕内容为空")
                    return None
                
                logger.info(f"成功提取字幕，内容长度: {len(subtitle_text)} 字符")
                
                # 保存字幕文本到文件（用于调试）
                subtitle_file = os.path.join(RESULTS_DIR, f"subtitle_{selected_lang}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
                with open(subtitle_file, 'w', encoding='utf-8') as f:
                    f.write(f"YouTube视频: {url}\n字幕语言: {selected_lang}\n字幕格式: {selected_format}\n\n")
                    f.write(subtitle_text)
                
                logger.info(f"字幕内容已保存至: {subtitle_file}")
                
                return {
                    'text': subtitle_text,
                    'language': selected_lang,
                    'format': selected_format,
                    'subtitle_file': subtitle_file,
                    'video_url': url
                }
                
            except requests.exceptions.RequestException as e:
                logger.error(f"下载字幕失败: {str(e)}")
                return None
            
    except Exception as e:
        logger.error(f"提取字幕时出错: {str(e)}")
        return None


def delete_file_from_oss(object_name):
    """
    从阿里云OSS删除文件

    参数:
        file_url: OSS文件URL

    返回:
        bool: 删除是否成功
    """
    try:
        logger.info(f"开始从OSS删除文件: {object_name}")

        # 创建OSS客户端
        if 'OSS_ACCESS_KEY_ID' in os.environ and 'OSS_ACCESS_KEY_SECRET' in os.environ:
            auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())
        else:
            auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)

        # 创建Bucket对象
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME, region=OSS_REGION)

        # 检查文件是否存在
        if not bucket.object_exists(object_name):
            logger.error(f"OSS文件不存在: {object_name}")
            return False

        # 删除文件
        response = bucket.delete_object(object_name)

        if response.status == HTTPStatus.NO_CONTENT:  # 204
            logger.info(f"文件删除成功: {object_name}")
            return True
        else:
            logger.error(f"文件删除失败，状态码: {response.status}")
            return False

    except oss2.exceptions.OssError as e:
        logger.error(f"OSS操作错误: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"删除OSS文件时出错: {str(e)}")
        return False

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='YouTube 音频下载、OSS 上传、语音识别和文本摘要')
    parser.add_argument('--url', type=str, help='YouTube 视频 URL')
    parser.add_argument('--oss-url', type=str, help='OSS 音频文件 URL, 直接用于语音识别测试')
    parser.add_argument('--text', type=str, help='直接输入要摘要的文本内容')
    parser.add_argument('--text-file', type=str, help='包含要摘要的文本文件路径')
    parser.add_argument('--skip-transcribe', action='store_true', help='跳过语音识别步骤')
    parser.add_argument('--skip-summary', action='store_true', help='跳过文本摘要步骤')
    parser.add_argument('--youtube-proxy', type=str, help='YouTube下载专用代理，格式如http://127.0.0.1:7890')
    parser.add_argument('--no-proxy', action='store_true', help='禁用所有代理设置（摘要功能始终不使用代理）')
    parser.add_argument('--use-subtitle', action='store_true', help='优先使用YouTube视频字幕（如果可用）')
    parser.add_argument('--force-audio', action='store_true', help='强制使用音频下载和转录流程，即使有字幕')
    args = parser.parse_args()
    
    # 处理全局代理设置
    if args.no_proxy:
        logger.info("禁用所有代理设置")
        # 清除所有代理环境变量
        for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy']:
            if proxy_var in os.environ:
                del os.environ[proxy_var]
        # 设置空代理
        os.environ['NO_PROXY'] = '*'
    
    # 0. 优先处理：如果提供了文本内容或文本文件，直接进行摘要测试
    if args.text or args.text_file:
        # 确定文本来源
        text_to_summarize = None
        source_description = None
        
        if args.text:
            # 直接使用提供的文本
            logger.info("使用命令行参数提供的文本进行摘要测试")
            text_to_summarize = args.text
            source_description = "命令行输入文本"
        elif args.text_file:
            # 从文件读取文本
            logger.info(f"从文件读取文本进行摘要测试: {args.text_file}")
            try:
                with open(args.text_file, 'r', encoding='utf-8') as f:
                    text_to_summarize = f.read()
                source_description = f"文件: {args.text_file}"
            except Exception as e:
                logger.error(f"读取文件时出错: {str(e)}")
                return 1
        
        if not text_to_summarize:
            logger.error("无法获取要摘要的文本内容")
            return 1
        
        # 调用摘要函数
        logger.info("开始生成文本摘要...")
        summary = summarize_text(text_to_summarize)
        
        if not summary:
            logger.error("摘要生成失败: 未返回结果")
            print("\n---------------------------------------")
            print("文本摘要生成失败。")
            print("错误信息: 未能生成摘要")
            print("---------------------------------------\n")
            return 1
        elif summary.startswith("摘要生成失败"):
            error_message = summary
            logger.error(f"摘要生成失败: {error_message}")
            print("\n---------------------------------------")
            print("文本摘要生成失败。")
            print(f"错误信息: {error_message}")
            print("---------------------------------------\n")
            return 1
        
        # 保存摘要结果到文件
        saved_file = save_transcription_result(text_to_summarize, summary, None, "summary")
        
        # 打印结果
        print("\n---------------------------------------")
        print(f"源文本 ({source_description}):")
        print("---------------------------------------")
        # 只打印前300个字符，然后是省略号
        if len(text_to_summarize) > 300:
            print(f"{text_to_summarize[:300]}...(省略{len(text_to_summarize)-300}个字符)")
        else:
            print(text_to_summarize)
        
        print("\n---------------------------------------")
        print("生成的摘要:")
        print("---------------------------------------")
        print(summary)
        
        if saved_file:
            print(f"\n完整结果已保存到: {saved_file}")
        
        print("---------------------------------------\n")
        return 0
        
    # 1. 如果提供了 OSS URL，直接进行语音识别测试
    if args.oss_url:
        logger.info(f"直接使用 OSS URL 进行语音识别测试: {args.oss_url}")
        result = transcribe_audio(args.oss_url, skip_summary=args.skip_summary)

        if 'error' in result:
            logger.error(f"音频转录失败: {result['error']}")
            return 1
        
        print("\n---------------------------------------")
        print(f"使用现有 OSS URL: {args.oss_url}")
        print("\n语音识别结果:")
        print(result['full_text'])
        
        if 'summary' in result and result['summary']:
            print("\n文本摘要:")
            print(result['summary'])
        
        if 'saved_file' in result:
            print(f"\n结果已保存到: {result['saved_file']}")
            
        print("---------------------------------------\n")
        return 0
    
    # 否则，执行完整流程
    # 获取 YouTube URL
    if args.url:
        url = args.url
    else:
        # 使用测试 URL - 选择一个公开视频
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - YouTube 第一个视频
        logger.info(f"使用测试 URL: {url}")
    
    # 新增流程：首先尝试提取YouTube字幕（除非明确指定使用音频流程）
    if not args.force_audio:
        logger.info("尝试从YouTube视频中提取字幕...")
        subtitle_result = extract_youtube_subtitles(url, proxy=args.youtube_proxy)
        
        if subtitle_result:
            logger.info(f"成功提取字幕，语言: {subtitle_result['language']}")
            
            # 使用提取的字幕文本直接进行摘要（除非指定跳过）
            if not args.skip_summary:
                logger.info("开始对字幕内容进行摘要...")
                summary = summarize_text(subtitle_result['text'])
                
                # 保存字幕文本和摘要到结果文件
                saved_file = save_transcription_result(
                    subtitle_result['text'], 
                    summary, 
                    f"YouTube字幕: {url}", 
                    "youtube_subtitle"
                )
                
                # 打印结果
                print("\n---------------------------------------")
                print(f"YouTube视频: {url}")
                print(f"已提取字幕，语言: {subtitle_result['language']}")
                print("\n字幕内容片段:")
                # 只显示前300个字符
                display_text = subtitle_result['text'][:300] + ("..." if len(subtitle_result['text']) > 300 else "")
                print(display_text)
                
                if summary and not summary.startswith("摘要生成失败"):
                    print("\n文本摘要:")
                    print(summary)
                else:
                    print("\n摘要生成失败:")
                    print(summary if summary else "未能生成摘要")
                
                if saved_file:
                    print(f"\n完整结果已保存到: {saved_file}")
                
                print("---------------------------------------\n")
                return 0
            else:
                # 如果跳过摘要，只显示字幕内容
                print("\n---------------------------------------")
                print(f"YouTube视频: {url}")
                print(f"已提取字幕，语言: {subtitle_result['language']}")
                print("\n字幕内容片段:")
                # 只显示前300个字符
                display_text = subtitle_result['text'][:300] + ("..." if len(subtitle_result['text']) > 300 else "")
                print(display_text)
                print(f"\n完整字幕已保存到: {subtitle_result['subtitle_file']}")
                print("---------------------------------------\n")
                return 0
        else:
            logger.info("未找到字幕或提取失败，将使用音频下载和转录流程")
    
    # 如果没有找到字幕或被指示使用音频流程，继续原有流程
    # 1. 从 YouTube 下载音频
    audio_file = download_audio_from_youtube(url, proxy=args.youtube_proxy)
    if not audio_file:
        logger.error("音频下载失败，程序退出")
        return 1
    
    # 2. 将音频文件上传到阿里云 OSS
    oss_url, object_name = upload_file_to_oss(audio_file)
    if not oss_url:
        logger.error("文件上传到 OSS 失败，程序退出")
        return 1
    
    # 3. 转录音频文件（除非指定跳过）
    if not args.skip_transcribe:
        result = transcribe_audio(oss_url, skip_summary=args.skip_summary)
        # 转录完成后删除OSS文件
        if delete_file_from_oss(object_name):
            logger.info("已清理OSS临时文件")
        else:
            logger.warning("OSS临时文件清理失败")

        if 'error' in result:
            logger.error(f"音频转录失败: {result['error']}")
            return 1
            
        # 4. 打印完整结果
        print("\n---------------------------------------")
        print(f"音频下载成功: {audio_file}")
        print(f"上传到 OSS 成功，访问 URL:")
        print(oss_url)
        print("\n语音识别结果:")
        print(result['full_text'])
        
        if 'summary' in result and result['summary']:
            print("\n文本摘要:")
            print(result['summary'])
        
        if 'saved_file' in result:
            print(f"\n结果已保存到: {result['saved_file']}")
            
        print("---------------------------------------\n")
    else:
        # 只打印 OSS URL
        print("\n---------------------------------------")
        print(f"音频下载成功: {audio_file}")
        print(f"上传到 OSS 成功，访问 URL:")
        print(oss_url)
        print("---------------------------------------\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 