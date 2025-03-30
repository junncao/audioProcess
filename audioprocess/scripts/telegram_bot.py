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
from telegram import Update, ParseMode
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from audioprocess.utils.logger import setup_logger, get_logger
from audioprocess.config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS
from audioprocess.main import process_youtube_video

# 设置日志
logger = get_logger(__name__)

# 创建一个队列用于存储日志消息
log_queue = Queue()

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

# 处理/start命令
def start(update: Update, context: CallbackContext) -> None:
    """发送欢迎消息"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    update.message.reply_text(
        f"👋 你好 {update.effective_user.first_name}!\n\n"
        "我是YouTube字幕摘要机器人。\n"
        "发送YouTube链接，我会提取并总结视频内容。\n\n"
        "支持命令:\n"
        "/start - 显示此帮助信息\n"
        "/help - 显示使用说明\n"
        "/cancel - 取消当前操作"
    )

# 处理/help命令
def help_command(update: Update, context: CallbackContext) -> None:
    """发送帮助消息"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    update.message.reply_text(
        "🔍 使用说明:\n\n"
        "1. 直接发送YouTube视频链接\n"
        "2. 机器人会提取视频字幕或下载音频并转录\n"
        "3. 自动生成内容摘要并发送给你\n\n"
        "注意: 处理大型视频可能需要较长时间，请耐心等待。"
    )

# 处理/cancel命令
def cancel(update: Update, context: CallbackContext) -> None:
    """取消当前操作"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    # 这里可以添加取消正在进行的处理任务的逻辑
    # 目前我们只返回一个消息
    update.message.reply_text("已取消当前操作。")

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

# 处理包含YouTube链接的消息
def handle_youtube_link(update: Update, context: CallbackContext) -> None:
    """处理YouTube链接"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    # 提取YouTube链接
    youtube_url = extract_youtube_link(update.message.text)
    if not youtube_url:
        update.message.reply_text("无法识别YouTube链接，请发送有效的YouTube URL。")
        return
    
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

# 处理视频的线程函数
def process_youtube_in_thread(youtube_url, update, context, progress_message):
    """在单独的线程中处理YouTube视频"""
    try:
        # 设置队列日志处理器
        setup_queue_logger()
        
        # 处理YouTube视频
        logger.info(f"开始处理YouTube链接: {youtube_url}")
        result = process_youtube_video(youtube_url, force_audio=False, skip_summary=False)
        
        # 等待一会，确保最后的日志都被处理
        time.sleep(1)
        
        # 发送最终结果
        send_final_result(update, context, progress_message, result)
        
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

# 发送最终处理结果，修改为发送文件和摘要内容
def send_final_result(update, context, progress_message, result):
    """发送处理完成的结果消息"""
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
    
    # 添加处理器
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("cancel", cancel))
    
    # 添加YouTube链接处理器
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.regex(YOUTUBE_REGEX),
        handle_youtube_link
    ))
    
    # 启动机器人
    logger.info("启动Telegram机器人")
    updater.start_polling()
    
    # 显示信息
    print(f"YouTube字幕摘要机器人已启动")
    print(f"允许的用户ID: {', '.join(TELEGRAM_ALLOWED_USERS) if TELEGRAM_ALLOWED_USERS else '所有用户'}")
    
    # 保持运行直到按下Ctrl-C
    updater.idle()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 