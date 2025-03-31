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
from telegram import Update, ParseMode, ReplyKeyboardMarkup, KeyboardButton, BotCommand, Bot
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)
import traceback

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from audioprocess.utils.logger import setup_logger, get_logger
from audioprocess.config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, 
    DASHSCOPE_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN,
    TRANSCRIPTION_RESULTS_DIR, TEMP_SUBTITLES_DIR, DOWNLOADS_DIR
)
from audioprocess.main import process_youtube_video
from audioprocess.core.youtube_downloader import download_audio_from_youtube
from audioprocess.core.summarization import summarize_text

# 设置日志
logger = get_logger(__name__)

# 创建一个队列用于存储日志消息
log_queue = Queue()

# 会话状态
MAIN = 0
YOUTUBE = 1  # 字幕摘要模式
SUMMARY = 2  # 摘要模式

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
        [KeyboardButton("📝 字幕摘要")],
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
        "我是YouTube字幕摘要助手，可以提取视频字幕并生成摘要\n\n"
        "使用方式：\n"
        "• 点击聊天框左侧的菜单按钮(/) 选择命令\n"
        "• 直接发送YouTube链接\n\n"
        "常用命令：\n"
        "/start - 返回主菜单\n"
        "/help - 查看详细使用说明",
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
        "🔍 *YouTube字幕摘要助手使用说明*\n\n"
        "*使用方式*\n"
        "1. 通过聊天框左侧的菜单按钮(/)选择命令\n"
        "2. 直接发送YouTube链接\n\n"
        "*📝 字幕摘要功能*\n"
        "发送YouTube链接，我会:\n"
        "• 提取视频字幕或下载音频并转录\n"
        "• 自动生成内容摘要\n"
        "• 发送摘要和完整文件\n\n"
        "*其他命令*:\n"
        "/start - 返回主菜单\n"
        "/help - 显示此帮助信息",
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

# 处理用户消息
def handle_message(update: Update, context: CallbackContext) -> int:
    """处理用户消息，主要处理YouTube链接"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return MAIN
    
    text = update.message.text
    
    # 检查是否为YouTube链接
    if is_youtube_link(text):
        # 启动后台线程处理YouTube视频
        thread = threading.Thread(
            target=process_youtube_in_thread,
            args=(update, context, text)
        )
        thread.daemon = True
        thread.start()
    else:
        update.message.reply_text(
            "⚠️ 请发送有效的YouTube链接。\n\n"
            "示例:\n"
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://youtu.be/dQw4w9WgXcQ"
        )
    
    return MAIN

# 处理视频的线程函数
def process_youtube_in_thread(update, context, text):
    """在单独的线程中处理YouTube视频"""
    try:
        # 设置队列日志处理器
        setup_queue_logger()
        
        # 处理YouTube视频前禁用所有代理，只在函数内部会使用代理
        original_proxies = disable_proxies()
        
        try:
            # 处理YouTube视频
            logger.info(f"开始处理YouTube链接: {text}")
            result = process_youtube_video(text, force_audio=False, skip_summary=False)
            
            # 等待一会，确保最后的日志都被处理
            time.sleep(1)
            
            # 发送最终结果
            send_final_result(update, context, result)
        finally:
            # 恢复原始代理设置
            restore_proxies(original_proxies)
        
    except Exception as e:
        error_message = f"处理视频时出错: {str(e)}"
        logger.error(error_message)
        try:
            update.message.reply_text(
                f"❌ {error_message}"
            )
        except Exception as edit_error:
            logger.error(f"发送错误消息失败: {str(edit_error)}")

# 发送最终处理结果，修改为发送文件和摘要内容
def send_final_result(update, context, result):
    """发送处理完成的结果消息"""
    # 确保禁用代理，避免发送文件时出错
    original_proxies = disable_proxies()
    
    try:
        if not result['success']:
            error_message = result.get('error', '未知错误')
            try:
                update.message.reply_text(
                    f"❌ 处理失败: {error_message}"
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
            update.message.reply_text(
                result_text + "请稍候，正在发送摘要和结果文件..."
            )
        except Exception as e:
            logger.error(f"发送结果状态消息出错: {str(e)}")
        
        # 发送摘要内容作为单独消息
        if 'summary' in result:
            summary_text = f"📝 摘要:\n\n{result['summary']}"
            try:
                update.message.reply_text(
                    summary_text
                )
            except Exception as e:
                logger.error(f"发送摘要消息出错: {str(e)}")
        elif 'summary_error' in result:
            try:
                update.message.reply_text(
                    f"⚠️ 摘要生成失败: {result['summary_error']}"
                )
            except Exception as e:
                logger.error(f"发送摘要错误消息出错: {str(e)}")
        
        # 发送结果文件
        if 'summary_file' in result and result['summary_file']:
            file_path = result['summary_file']
            try:
                with open(file_path, 'rb') as file:
                    update.message.reply_document(
                        document=file,
                        filename=os.path.basename(file_path),
                        caption="📋 完整转录和摘要结果文件"
                    )
            except Exception as e:
                logger.error(f"发送摘要文件出错: {str(e)}")
                # 如果文件发送失败，至少发送文件路径
                try:
                    update.message.reply_text(
                        f"📋 无法发送文件，结果已保存到: {file_path}"
                    )
                except:
                    pass
        elif 'subtitle_file' in result and result['subtitle_file']:
            file_path = result['subtitle_file']
            try:
                with open(file_path, 'rb') as file:
                    update.message.reply_document(
                        document=file,
                        filename=os.path.basename(file_path),
                        caption="📋 字幕文件"
                    )
            except Exception as e:
                logger.error(f"发送字幕文件出错: {str(e)}")
                # 如果文件发送失败，至少发送文件路径
                try:
                    update.message.reply_text(
                        f"📋 无法发送文件，字幕已保存到: {file_path}"
                    )
                except:
                    pass
        elif 'transcription_file' in result and result['transcription_file']:
            file_path = result['transcription_file']
            try:
                with open(file_path, 'rb') as file:
                    update.message.reply_document(
                        document=file,
                        filename=os.path.basename(file_path),
                        caption="📋 转录结果文件"
                    )
            except Exception as e:
                logger.error(f"发送转录文件出错: {str(e)}")
                # 如果文件发送失败，至少发送文件路径
                try:
                    update.message.reply_text(
                        f"📋 无法发送文件，转录结果已保存到: {file_path}"
                    )
                except:
                    pass
        else:
            try:
                update.message.reply_text(
                    "⚠️ 未生成结果文件"
                )
            except Exception as e:
                logger.error(f"发送无文件消息出错: {str(e)}")
    finally:
        # 恢复代理设置
        restore_proxies(original_proxies)

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

# 添加错误处理函数定义
def error_handler(update, context):
    """处理错误"""
    logger.error(f"更新 {update} 导致错误 {context.error}")
    try:
        if update and update.effective_message:
            update.effective_message.reply_text("发生错误，请稍后重试。")
    except:
        pass

def clean_updates(bot_token):
    """清除机器人的挂起更新"""
    try:
        logger.info(f"清除机器人挂起的更新 (Token: {bot_token[:10]}...{bot_token[-5:]})")
        bot = Bot(bot_token)
        bot.delete_webhook()
        updates = bot.get_updates(offset=-1, limit=1)
        if updates:
            logger.info(f"清除了 {len(updates)} 个挂起的更新")
        else:
            logger.info("没有挂起的更新需要清除")
    except Exception as e:
        logger.error(f"清除更新时出错: {str(e)}", exc_info=True)

def start_summary_bot():
    """启动字幕摘要机器人"""
    try:
        logger.info("正在启动字幕摘要机器人...")
        # 确保目录存在
        os.makedirs(TRANSCRIPTION_RESULTS_DIR, exist_ok=True)
        os.makedirs(TEMP_SUBTITLES_DIR, exist_ok=True)
        
        # 清除任何挂起的更新
        clean_updates(TELEGRAM_BOT_TOKEN)
        
        # 创建Updater和Dispatcher
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # 设置命令菜单(显示在输入框左侧)
        commands = [
            BotCommand("start", "启动机器人/返回主菜单"),
            BotCommand("summary", "字幕摘要模式"),
            BotCommand("help", "显示帮助信息")
        ]
        updater.bot.set_my_commands(commands)
        
        # 创建会话处理器
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start), CommandHandler('summary', summary_mode)],
            states={
                MAIN: [
                    CommandHandler('summary', summary_mode),
                    MessageHandler(Filters.text & ~Filters.command, handle_message),
                ],
                SUMMARY: [
                    MessageHandler(Filters.text & ~Filters.command, handle_summary),
                    CommandHandler('start', start),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # 添加处理器
        dispatcher.add_handler(conv_handler)
        dispatcher.add_handler(CommandHandler("help", help_command))
        
        # 添加错误处理器
        dispatcher.add_error_handler(error_handler)
        
        # 启动机器人 - 使用start_polling而不是idle()来避免阻塞
        logger.info("启动字幕摘要机器人轮询...")
        
        # 首先删除webhook并清除任何待处理的更新
        updater.bot.delete_webhook()
        
        # 启动轮询，设置drop_pending_updates=True避免处理积压的消息
        updater.start_polling(drop_pending_updates=True)
        logger.info("字幕摘要机器人轮询已启动")
        
        return updater  # 返回updater对象以便主程序可以控制
    except Exception as e:
        logger.error(f"启动字幕摘要机器人时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def start_audio_download_bot():
    """启动音频下载机器人"""
    try:
        from audioprocess.scripts.audio_download_bot import main as start_audio_bot
        logger.info("正在启动音频下载机器人...")
        
        # 确保目录存在
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        
        # 清除任何挂起的更新，确保没有冲突
        clean_updates(TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN)
        
        # 启动音频下载机器人
        audio_bot_updater = start_audio_bot()
        logger.info("音频下载机器人已启动")
        
        return audio_bot_updater
    except Exception as e:
        logger.error(f"启动音频下载机器人时出错: {str(e)}", exc_info=True)
        return None

def summary_mode(update: Update, context: CallbackContext) -> int:
    """进入字幕摘要模式"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return MAIN
    
    update.message.reply_text(
        "已进入字幕摘要模式。请发送YouTube链接，我将提取视频字幕并生成摘要。\n\n"
        "您可以随时发送 /start 命令返回主菜单。"
    )
    return SUMMARY

def handle_summary(update: Update, context: CallbackContext) -> int:
    """处理字幕摘要模式下的用户消息"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return MAIN
    
    # 检查是否为YouTube链接
    if is_youtube_url(text):
        # 启动后台线程处理YouTube视频
        thread = threading.Thread(
            target=process_youtube_in_thread,
            args=(update, context, text)
        )
        thread.daemon = True
        thread.start()
    else:
        update.message.reply_text(
            "⚠️ 请发送有效的YouTube链接。\n\n"
            "示例:\n"
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://youtu.be/dQw4w9WgXcQ"
        )
    
    return SUMMARY

def main():
    """启动机器人"""
    # 检查是否设置了TOKEN
    if not TELEGRAM_BOT_TOKEN:
        logger.error("未设置TELEGRAM_BOT_TOKEN环境变量或配置")
        print("错误: 请在环境变量或配置文件中设置TELEGRAM_BOT_TOKEN")
        return 1
    
    try:
        # 创建Updater和Dispatcher
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # 设置命令菜单(显示在输入框左侧)
        commands = [
            BotCommand("start", "启动机器人/返回主菜单"),
            BotCommand("summary", "字幕摘要模式"),
            BotCommand("help", "显示帮助信息")
        ]
        updater.bot.set_my_commands(commands)
        
        # 创建会话处理器
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start), CommandHandler('summary', summary_mode)],
            states={
                MAIN: [
                    CommandHandler('summary', summary_mode),
                    MessageHandler(Filters.text & ~Filters.command, handle_message),
                ],
                SUMMARY: [
                    MessageHandler(Filters.text & ~Filters.command, handle_summary),
                    CommandHandler('start', start),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # 添加处理器
        dispatcher.add_handler(conv_handler)
        dispatcher.add_handler(CommandHandler("help", help_command))
        
        # 添加错误处理器
        dispatcher.add_error_handler(error_handler)
        
        # 启动机器人 - 使用start_polling而不是idle()来避免阻塞
        logger.info("启动字幕摘要机器人轮询...")
        
        # 首先删除webhook并清除任何待处理的更新
        updater.bot.delete_webhook()
        
        # 启动轮询，设置drop_pending_updates=True避免处理积压的消息
        updater.start_polling(drop_pending_updates=True)
        logger.info("字幕摘要机器人轮询已启动")
        
        return updater  # 返回updater对象以便主程序可以控制
    
    except Exception as e:
        logger.error(f"启动字幕摘要机器人时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    try:
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('telegram_bot.log')
            ]
        )
        
        logger.info("======= 启动Telegram机器人服务 =======")
        
        # 第一步：启动字幕摘要机器人
        summary_updater = start_summary_bot()
        if not summary_updater:
            logger.error("字幕摘要机器人启动失败，终止程序")
            sys.exit(1)
            
        # 等待几秒钟，让第一个机器人完全初始化
        logger.info("等待字幕摘要机器人初始化完成...")
        time.sleep(3)
        
        # 第二步：启动音频下载机器人
        audio_updater = start_audio_download_bot()
        if not audio_updater:
            logger.error("音频下载机器人启动失败，但字幕摘要机器人将继续运行")
            # 只运行字幕摘要机器人
            summary_updater.idle()
        else:
            # 两个机器人都成功启动，继续运行
            logger.info("两个机器人都已成功启动，进入idle状态")
            # 使用任意一个updater的idle方法来保持程序运行
            summary_updater.idle()
            
    except Exception as e:
        logger.error(f"启动Telegram机器人服务时发生错误: {str(e)}", exc_info=True)
        sys.exit(1) 