#!/usr/bin/env python3
"""
YouTube字幕摘要Telegram机器人
---------------------------
接收YouTube视频链接，提取字幕或转录音频，生成摘要并发送结果
"""

import os
import re
import sys
import time
import logging
import asyncio
import threading
from queue import Queue, Empty
from telegram import Update, ParseMode, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from audioprocess.utils.logger import setup_logger, get_logger
from audioprocess.config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, 
    DASHSCOPE_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
)
from audioprocess.main import process_youtube_video
from audioprocess.core.youtube_downloader import download_audio_from_youtube
from audioprocess.core.summarization import summarize_text

# 设置日志
logger = get_logger(__name__)

# 创建一个队列用于存储日志消息
log_queue = Queue()

# 对话状态定义
MAIN, SUMMARY, DOWNLOAD, CHAT = range(4)

# 自定义日志处理器，将日志添加到队列
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)

# 添加队列处理器到根日志记录器
def setup_queue_logger():
    root_logger = logging.getLogger()
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))
    queue_handler.setLevel(logging.INFO)
    root_logger.addHandler(queue_handler)

# YouTube URL正则表达式
YOUTUBE_REGEX = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

# 创建主菜单键盘
def get_main_keyboard():
    """创建主菜单键盘"""
    keyboard = [
        [KeyboardButton("📝 字幕摘要"), KeyboardButton("🎵 音频下载")],
        [KeyboardButton("🤖 AI对话")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# 处理/start命令
def start(update: Update, context: CallbackContext) -> int:
    """发送欢迎消息并显示主菜单"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return ConversationHandler.END
    
    update.message.reply_text(
        f"👋 你好 {update.effective_user.first_name}!\n\n"
        "我是YouTube视频助手，可以提供以下功能：\n\n"
        "1️⃣ 📝 *字幕摘要*：提取视频字幕并生成摘要\n"
        "2️⃣ 🎵 *音频下载*：下载视频的音频文件\n"
        "3️⃣ 🤖 *AI对话*：使用阿里云大模型进行对话\n\n"
        "使用方式：\n"
        "• 点击聊天框左侧的菜单按钮(/) 选择命令\n"
        "• 使用下方的快捷按钮选择功能\n"
        "• 直接发送YouTube链接(默认使用摘要功能)\n\n"
        "常用命令：\n"
        "/summary - 字幕摘要模式\n"
        "/download - 音频下载模式\n"
        "/chat - AI对话模式\n"
        "/help - 查看详细使用说明\n"
        "/cancel - 取消当前操作",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return MAIN

# 处理/help命令
def help_command(update: Update, context: CallbackContext) -> None:
    """发送帮助消息"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    update.message.reply_text(
        "🔍 *详细使用说明*\n\n"
        "*使用方式*\n"
        "1. 通过聊天框左侧的菜单按钮(/)选择命令\n"
        "2. 点击下方快捷按钮选择功能\n"
        "3. 直接发送YouTube链接（默认使用摘要功能）\n\n"
        "*📝 字幕摘要功能* `/summary`\n"
        "发送YouTube链接，我会:\n"
        "• 提取视频字幕或下载音频并转录\n"
        "• 自动生成内容摘要\n"
        "• 发送摘要和完整文件\n\n"
        "*🎵 音频下载功能* `/download`\n"
        "发送YouTube链接，我会:\n"
        "• 下载视频的WebM音频文件\n"
        "• 将音频文件发送给你\n\n"
        "*🤖 AI对话功能* `/chat`\n"
        "• 选择此功能后直接发消息\n"
        "• 使用阿里云大模型进行回答\n"
        "• 发送'/exit'退出对话模式\n\n"
        "*其他命令*:\n"
        "/start - 返回主菜单\n"
        "/help - 显示此帮助信息\n"
        "/cancel - 取消当前操作",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# 处理/cancel命令
def cancel(update: Update, context: CallbackContext) -> int:
    """取消当前操作并返回主菜单"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return ConversationHandler.END
    
    # 清除会话数据
    context.user_data.clear()
    
    update.message.reply_text(
        "已取消当前操作，返回主菜单。", 
        reply_markup=get_main_keyboard()
    )
    
    return MAIN

# 进入字幕摘要模式
def enter_summary_mode(update: Update, context: CallbackContext) -> int:
    """进入字幕摘要模式"""
    update.message.reply_text(
        "📝 已进入*字幕摘要*模式\n\n"
        "请发送YouTube视频链接，我将提取字幕并生成摘要。\n"
        "发送 /cancel 返回主菜单。",
        parse_mode=ParseMode.MARKDOWN
    )
    return SUMMARY

# 进入音频下载模式
def enter_download_mode(update: Update, context: CallbackContext) -> int:
    """进入音频下载模式"""
    update.message.reply_text(
        "🎵 已进入*音频下载*模式\n\n"
        "请发送YouTube视频链接，我将下载并发送音频文件。\n"
        "发送 /cancel 返回主菜单。",
        parse_mode=ParseMode.MARKDOWN
    )
    return DOWNLOAD

# 进入AI对话模式
def enter_chat_mode(update: Update, context: CallbackContext) -> int:
    """进入AI对话模式"""
    update.message.reply_text(
        "🤖 已进入*AI对话*模式\n\n"
        "现在可以直接发送消息，我将使用阿里云大模型回答。\n"
        "发送 /exit 退出对话模式。\n"
        "发送 /cancel 返回主菜单。",
        parse_mode=ParseMode.MARKDOWN
    )
    return CHAT

# 退出AI对话模式
def exit_chat_mode(update: Update, context: CallbackContext) -> int:
    """退出AI对话模式"""
    update.message.reply_text(
        "已退出AI对话模式，返回主菜单。",
        reply_markup=get_main_keyboard()
    )
    return MAIN

# 检查消息是否包含YouTube链接
def is_youtube_link(text):
    """检查文本是否包含YouTube链接"""
    return bool(re.search(YOUTUBE_REGEX, text))

# 从文本中提取YouTube链接
def extract_youtube_link(text):
    """从文本中提取YouTube链接"""
    match = re.search(YOUTUBE_REGEX, text)
    if match:
        video_id = match.group(6)
        return f"https://www.youtube.com/watch?v={video_id}"
    return None

# 处理菜单选择
def handle_menu_choice(update: Update, context: CallbackContext) -> int:
    """处理菜单选择"""
    text = update.message.text
    
    if "字幕摘要" in text:
        return enter_summary_mode(update, context)
    elif "音频下载" in text:
        return enter_download_mode(update, context)
    elif "AI对话" in text:
        return enter_chat_mode(update, context)
    else:
        # 检查是否包含YouTube链接
        if is_youtube_link(text):
            # 默认使用摘要功能处理链接
            return handle_summary_request(update, context)
        else:
            update.message.reply_text(
                "请从菜单中选择功能，或发送有效的YouTube链接。",
                reply_markup=get_main_keyboard()
            )
            return MAIN

# 处理字幕摘要请求
def handle_summary_request(update: Update, context: CallbackContext) -> int:
    """处理字幕摘要请求"""
    # 提取YouTube链接
    youtube_url = extract_youtube_link(update.message.text)
    if not youtube_url:
        update.message.reply_text("无法识别YouTube链接，请发送有效的YouTube URL。")
        return SUMMARY
    
    # 发送初始处理消息
    progress_message = update.message.reply_text(
        f"🔄 开始处理YouTube视频...\n{youtube_url}\n\n"
        "请稍候，正在提取字幕或转录音频..."
    )
    
    # 创建日志接收器和更新者
    log_collector = LogCollector(update, context, progress_message)
    log_collector.start()
    
    # 在单独的线程中处理视频，避免阻塞主线程
    process_thread = threading.Thread(
        target=process_youtube_in_thread,
        args=(youtube_url, update, context, progress_message)
    )
    process_thread.start()
    
    return SUMMARY

# 处理音频下载请求
def handle_download_request(update: Update, context: CallbackContext) -> int:
    """处理音频下载请求"""
    # 提取YouTube链接
    youtube_url = extract_youtube_link(update.message.text)
    if not youtube_url:
        update.message.reply_text("无法识别YouTube链接，请发送有效的YouTube URL。")
        return DOWNLOAD
    
    # 发送初始处理消息
    progress_message = update.message.reply_text(
        f"🔄 开始下载音频...\n{youtube_url}\n\n"
        "请稍候，正在从YouTube下载音频文件..."
    )
    
    # 在单独的线程中下载音频，避免阻塞主线程
    download_thread = threading.Thread(
        target=download_audio_in_thread,
        args=(youtube_url, update, context, progress_message)
    )
    download_thread.start()
    
    return DOWNLOAD

# 处理AI对话请求
def handle_chat_request(update: Update, context: CallbackContext) -> int:
    """处理AI对话请求"""
    # 获取用户消息
    user_message = update.message.text
    
    # 特殊命令处理
    if user_message.startswith('/'):
        if user_message == '/exit':
            return exit_chat_mode(update, context)
        elif user_message == '/cancel':
            return cancel(update, context)
        else:
            update.message.reply_text("未知命令，继续对话或发送 /exit 退出对话模式。")
            return CHAT
    
    # 发送处理中提示
    progress_message = update.message.reply_text("🤔 思考中...")
    
    # 在单独的线程中调用AI模型，避免阻塞主线程
    chat_thread = threading.Thread(
        target=process_chat_in_thread,
        args=(user_message, update, context, progress_message)
    )
    chat_thread.start()
    
    return CHAT

# AI对话处理线程
def process_chat_in_thread(user_message, update, context, progress_message):
    """在线程中处理AI对话请求"""
    try:
        # 导入OpenAI客户端
        from openai import OpenAI
        
        # 禁用所有代理设置，避免SOCKS代理错误
        original_proxies = disable_proxies()
        
        try:
            # 创建OpenAI客户端
            client_kwargs = {
                'api_key': DASHSCOPE_API_KEY,
                'base_url': OPENAI_BASE_URL,
            }
            client = OpenAI(**client_kwargs)
            
            # 保存对话历史（如果有）
            if 'chat_history' not in context.user_data:
                context.user_data['chat_history'] = []
            
            # 准备消息列表，包括系统指令和历史对话
            messages = [
                {'role': 'system', 'content': '你是阿里云大模型，请提供简洁、友好、有见地的回答。'}
            ]
            
            # 添加历史对话（最多保留10轮）
            for msg in context.user_data['chat_history'][-10:]:
                messages.append(msg)
            
            # 添加当前用户消息
            messages.append({'role': 'user', 'content': user_message})
            
            # 调用API获取回复
            try:
                completion = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    timeout=60
                )
                
                # 提取回复文本
                reply = completion.choices[0].message.content
                
                # 保存到对话历史
                context.user_data['chat_history'].append({'role': 'user', 'content': user_message})
                context.user_data['chat_history'].append({'role': 'assistant', 'content': reply})
                
                # 发送回复
                context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=progress_message.message_id,
                    text=reply
                )
                
            except Exception as e:
                error_message = f"AI调用失败: {str(e)}"
                logger.error(error_message)
                context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=progress_message.message_id,
                    text=f"❌ {error_message}"
                )
        finally:
            # 恢复原始代理设置
            restore_proxies(original_proxies)
            
    except Exception as e:
        logger.error(f"处理AI对话时出错: {str(e)}")
        try:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=f"❌ 处理对话请求时出错: {str(e)}"
            )
        except:
            pass

# 音频下载线程函数
def download_audio_in_thread(youtube_url, update, context, progress_message):
    """在线程中下载音频文件"""
    try:
        # 下载音频 - 注意：这是我们唯一需要使用代理的功能
        # 因此我们不在这里禁用代理，让download_audio_from_youtube函数内部使用系统代理
        logger.info(f"开始从URL下载音频: {youtube_url}")
        audio_file = download_audio_from_youtube(youtube_url)
        
        if not audio_file:
            error_message = "音频下载失败"
            logger.error(error_message)
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=f"❌ {error_message}"
            )
            return
        
        # 发送下载完成消息
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=progress_message.message_id,
            text=f"✅ 音频下载成功!\n\n正在上传音频文件..."
        )
        
        # 发送音频文件前禁用代理
        original_proxies = disable_proxies()
        try:
            # 发送音频文件
            try:
                with open(audio_file, 'rb') as file:
                    context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=file,
                        title=os.path.basename(audio_file),
                        caption=f"🎵 YouTube音频: {youtube_url}"
                    )
            except Exception as e:
                logger.error(f"发送音频文件失败: {str(e)}")
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ 音频文件太大，无法直接发送。已保存到: {audio_file}"
                )
        finally:
            # 恢复代理设置
            restore_proxies(original_proxies)
            
    except Exception as e:
        error_message = f"处理下载请求时出错: {str(e)}"
        logger.error(error_message)
        try:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=f"❌ {error_message}"
            )
        except:
            pass

# 日志收集器类，修改以解决"Message is not modified"错误
class LogCollector:
    def __init__(self, update, context, message):
        self.update = update
        self.context = context
        self.message = message
        self.running = True
        self.logs = []
        self.last_update_time = 0
        self.last_message_text = ""  # 记录上一次发送的消息内容
        
    def start(self):
        """启动日志收集器线程"""
        self.thread = threading.Thread(target=self.collect_logs)
        self.thread.daemon = True
        self.thread.start()
        
    def collect_logs(self):
        """收集日志并定期更新消息"""
        import time
        
        while self.running:
            try:
                # 从队列中获取日志消息
                new_logs_added = False
                while not log_queue.empty():
                    log = log_queue.get_nowait()
                    self.logs.append(log)
                    new_logs_added = True
                    log_queue.task_done()
                
                # 每3秒更新一次消息，并且仅当有新日志或上次更新超过10秒时更新
                current_time = time.time()
                should_update = (
                    (current_time - self.last_update_time >= 3 and new_logs_added) or
                    (current_time - self.last_update_time >= 10)
                ) and self.logs
                
                if should_update:
                    # 只保留最新的10条日志
                    recent_logs = self.logs[-10:]
                    log_text = "\n".join(recent_logs)
                    
                    message_text = (
                        f"🔄 处理中...\n\n"
                        f"最新日志:\n```\n{log_text}\n```"
                    )
                    
                    # 只有消息内容变化时才更新
                    if message_text != self.last_message_text:
                        try:
                            self.context.bot.edit_message_text(
                                chat_id=self.update.effective_chat.id,
                                message_id=self.message.message_id,
                                text=message_text,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            self.last_message_text = message_text
                            self.last_update_time = current_time
                        except Exception as e:
                            if "Message is not modified" not in str(e):
                                logger.error(f"更新消息失败: {str(e)}")
                    else:
                        # 即使内容相同，也更新时间戳避免频繁尝试
                        self.last_update_time = current_time
                
                time.sleep(1)
                
            except Empty:
                # 队列为空，继续等待
                time.sleep(1)
                continue
            except Exception as e:
                logger.error(f"日志收集器出错: {str(e)}")
                time.sleep(1)

# 代理管理辅助函数
def disable_proxies():
    """禁用所有代理设置并返回原始设置"""
    original_proxies = {}
    for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
        if proxy_var in os.environ:
            original_proxies[proxy_var] = os.environ[proxy_var]
            del os.environ[proxy_var]
    
    # 明确禁用所有代理
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    
    return original_proxies

def restore_proxies(original_proxies):
    """恢复原始代理设置"""
    # 首先清除NO_PROXY设置
    if 'NO_PROXY' in os.environ:
        del os.environ['NO_PROXY']
    if 'no_proxy' in os.environ:
        del os.environ['no_proxy']
    
    # 然后恢复原始设置
    for proxy_var, value in original_proxies.items():
        os.environ[proxy_var] = value

# 处理视频的线程函数
def process_youtube_in_thread(youtube_url, update, context, progress_message):
    """在单独的线程中处理YouTube视频"""
    try:
        # 设置队列日志处理器
        setup_queue_logger()
        
        # 处理YouTube视频前禁用所有代理，只在函数内部会使用代理
        original_proxies = disable_proxies()
        
        try:
            # 处理YouTube视频
            logger.info(f"开始处理YouTube链接: {youtube_url}")
            result = process_youtube_video(youtube_url, force_audio=False, skip_summary=False)
            
            # 等待一会，确保最后的日志都被处理
            time.sleep(1)
            
            # 发送最终结果
            send_final_result(update, context, progress_message, result)
        finally:
            # 恢复原始代理设置
            restore_proxies(original_proxies)
        
    except Exception as e:
        error_message = f"处理视频时出错: {str(e)}"
        logger.error(error_message)
        try:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=f"❌ {error_message}"
            )
        except Exception as edit_error:
            logger.error(f"发送错误消息失败: {str(edit_error)}")

# 发送最终处理结果，修改为发送文件和摘要内容
def send_final_result(update, context, progress_message, result):
    """发送处理完成的结果消息"""
    # 确保禁用代理，避免发送文件时出错
    original_proxies = disable_proxies()
    
    try:
        if not result['success']:
            error_message = result.get('error', '未知错误')
            try:
                context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=progress_message.message_id,
                    text=f"❌ 处理失败: {error_message}"
                )
            except Exception as e:
                logger.error(f"发送失败消息出错: {str(e)}")
            return
        
        # 构建结果消息
        result_text = "✅ 处理完成!\n\n"
        
        # 添加来源信息
        if 'subtitle_extracted' in result and result['subtitle_extracted']:
            result_text += f"📑 已提取字幕，语言: {result.get('language', '未知')}\n\n"
        elif 'audio_file' in result:
            result_text += "🔊 已下载并转录音频\n\n"
        
        # 发送结果状态消息
        try:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=progress_message.message_id,
                text=result_text + "请稍候，正在发送摘要和结果文件..."
            )
        except Exception as e:
            logger.error(f"发送结果状态消息出错: {str(e)}")
        
        # 发送摘要内容作为单独消息
        if 'summary' in result:
            summary_text = f"📝 摘要:\n\n{result['summary']}"
            try:
                context.bot.send_message(
                    chat_id=update.effective_chat.id, 
                    text=summary_text
                )
            except Exception as e:
                logger.error(f"发送摘要消息出错: {str(e)}")
        elif 'summary_error' in result:
            try:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ 摘要生成失败: {result['summary_error']}"
                )
            except Exception as e:
                logger.error(f"发送摘要错误消息出错: {str(e)}")
        
        # 发送结果文件
        if 'summary_file' in result and result['summary_file']:
            file_path = result['summary_file']
            try:
                with open(file_path, 'rb') as file:
                    context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename=os.path.basename(file_path),
                        caption="📋 完整转录和摘要结果文件"
                    )
            except Exception as e:
                logger.error(f"发送摘要文件出错: {str(e)}")
                # 如果文件发送失败，至少发送文件路径
                try:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"📋 无法发送文件，结果已保存到: {file_path}"
                    )
                except:
                    pass
        elif 'subtitle_file' in result and result['subtitle_file']:
            file_path = result['subtitle_file']
            try:
                with open(file_path, 'rb') as file:
                    context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename=os.path.basename(file_path),
                        caption="📋 字幕文件"
                    )
            except Exception as e:
                logger.error(f"发送字幕文件出错: {str(e)}")
                # 如果文件发送失败，至少发送文件路径
                try:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"📋 无法发送文件，字幕已保存到: {file_path}"
                    )
                except:
                    pass
        elif 'transcription_file' in result and result['transcription_file']:
            file_path = result['transcription_file']
            try:
                with open(file_path, 'rb') as file:
                    context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename=os.path.basename(file_path),
                        caption="📋 转录结果文件"
                    )
            except Exception as e:
                logger.error(f"发送转录文件出错: {str(e)}")
                # 如果文件发送失败，至少发送文件路径
                try:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"📋 无法发送文件，转录结果已保存到: {file_path}"
                    )
                except:
                    pass
        else:
            try:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ 未生成结果文件"
                )
            except Exception as e:
                logger.error(f"发送无文件消息出错: {str(e)}")
    finally:
        # 恢复代理设置
        restore_proxies(original_proxies)

# 主函数
def main():
    """启动机器人"""
    # 检查是否设置了TOKEN
    if not TELEGRAM_BOT_TOKEN:
        logger.error("未设置TELEGRAM_BOT_TOKEN环境变量或配置")
        print("错误: 请在环境变量或配置文件中设置TELEGRAM_BOT_TOKEN")
        return 1
    
    # 创建Updater和Dispatcher
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # 设置命令菜单(显示在输入框左侧)
    commands = [
        BotCommand("start", "启动机器人/返回主菜单"),
        BotCommand("summary", "字幕摘要模式 - 提取视频字幕并生成摘要"),
        BotCommand("download", "音频下载模式 - 下载视频音频"),
        BotCommand("chat", "AI对话模式 - 与阿里云大模型对话"),
        BotCommand("help", "显示帮助信息"),
        BotCommand("cancel", "取消当前操作")
    ]
    updater.bot.set_my_commands(commands)
    
    # 创建会话处理器
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('summary', enter_summary_mode),
            CommandHandler('download', enter_download_mode),
            CommandHandler('chat', enter_chat_mode),
            MessageHandler(Filters.text & ~Filters.command, handle_menu_choice)
        ],
        states={
            MAIN: [
                CommandHandler('help', help_command),
                CommandHandler('summary', enter_summary_mode),
                CommandHandler('download', enter_download_mode),
                CommandHandler('chat', enter_chat_mode),
                MessageHandler(Filters.text & ~Filters.command, handle_menu_choice)
            ],
            SUMMARY: [
                CommandHandler('cancel', cancel),
                MessageHandler(Filters.text & ~Filters.command, handle_summary_request)
            ],
            DOWNLOAD: [
                CommandHandler('cancel', cancel),
                MessageHandler(Filters.text & ~Filters.command, handle_download_request)
            ],
            CHAT: [
                CommandHandler('exit', exit_chat_mode),
                CommandHandler('cancel', cancel),
                MessageHandler(Filters.text & ~Filters.command, handle_chat_request)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name="bot_conversation",
        persistent=False
    )
    
    # 添加会话处理器
    dispatcher.add_handler(conv_handler)
    
    # 添加帮助处理器（在对话处理器之外也可访问）
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # 启动机器人
    logger.info("启动Telegram机器人")
    updater.start_polling()
    
    # 显示信息
    print(f"YouTube视频助手机器人已启动")
    print(f"允许的用户ID: {', '.join(TELEGRAM_ALLOWED_USERS) if TELEGRAM_ALLOWED_USERS else '所有用户'}")
    
    # 保持运行直到按下Ctrl-C
    updater.idle()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 