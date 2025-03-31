#!/usr/bin/env python3
"""
YouTube音频下载 Telegram机器人
----------------------------
专门用于下载YouTube视频的音频(WebM格式)并发送到Telegram聊天
"""

import os
import logging
import threading
from queue import Queue
from telegram import Update, ParseMode, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)
import re

# 导入项目模块
from audioprocess.config.settings import (
    TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN,
    TELEGRAM_ALLOWED_USERS,
    DOWNLOADS_DIR
)

# 导入音频下载功能
from audioprocess.utils.youtube_utils import download_audio_from_youtube

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audio_bot.log'))  # 输出到文件
    ]
)
logger = logging.getLogger(__name__)

# 会话状态
MAIN = 0

# YouTube链接匹配模式
YOUTUBE_PATTERN = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'

def is_youtube_url(text):
    """检查文本是否是YouTube URL"""
    match = re.search(YOUTUBE_PATTERN, text)
    return bool(match)

def start(update: Update, context: CallbackContext) -> int:
    """发送欢迎消息并显示主菜单"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return ConversationHandler.END
    
    update.message.reply_text(
        f"👋 你好 {update.effective_user.first_name}!\n\n"
        "我是YouTube音频下载助手\n\n"
        "发送YouTube链接，我会下载视频的音频文件(WebM格式)并发送给你。\n\n"
        "命令列表:\n"
        "/start - 显示此欢迎信息\n"
        "/help - 显示帮助信息"
    )
    
    return MAIN

def help_command(update: Update, context: CallbackContext) -> None:
    """发送帮助消息"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    update.message.reply_text(
        "🔍 *YouTube音频下载助手使用说明*\n\n"
        "*使用方式*\n"
        "1. 从YouTube、优兔等网站复制视频链接\n"
        "2. 将链接粘贴并发送给我\n"
        "3. 等待下载完成\n"
        "4. 接收音频文件(WebM格式)\n\n"
        "*支持的网站*\n"
        "• YouTube (youtube.com)\n"
        "• YouTu.be (youtu.be)\n\n"
        "*命令*:\n"
        "/start - 返回主菜单\n"
        "/help - 显示此帮助信息",
        parse_mode=ParseMode.MARKDOWN
    )

def download_audio_in_thread(update, context, url):
    """在后台线程中下载音频并发送到Telegram"""
    # 发送处理中消息
    message = update.message.reply_text("⏳ 正在处理YouTube链接...")
    
    try:
        logger.info(f"开始处理下载请求: {url}")
        
        # 保存原始代理设置
        original_proxies = {}
        for proxy_var in ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy', 'NO_PROXY', 'no_proxy']:
            if proxy_var in os.environ:
                original_proxies[proxy_var] = os.environ[proxy_var]
        
        logger.info(f"保存的代理设置: {original_proxies}")
        
        try:
            # 下载音频文件
            message.edit_text("⏳ 正在从YouTube下载音频...")
            logger.info(f"开始下载音频: {url}")
            audio_file = download_audio_from_youtube(url, output_path=DOWNLOADS_DIR)
            
            if not audio_file:
                logger.error(f"下载失败: {url}")
                message.edit_text("❌ 下载失败！无法从提供的链接下载音频。")
                return
            
            logger.info(f"下载成功: {audio_file}")
            
            # 通知用户下载完成,准备发送
            message.edit_text("✅ 下载完成！正在发送音频文件...")
            
            # 禁用代理发送文件
            logger.info("禁用代理以发送文件")
            os.environ['NO_PROXY'] = '*'
            
            # 发送音频文件
            try:
                logger.info(f"开始发送音频文件: {audio_file}")
                with open(audio_file, 'rb') as audio:
                    update.message.reply_document(
                        document=audio,
                        filename=os.path.basename(audio_file),
                        caption=f"🎵 从YouTube下载的音频文件"
                    )
                logger.info("音频文件发送成功")
            except Exception as send_error:
                logger.error(f"发送音频文件失败: {str(send_error)}")
                update.message.reply_text(f"❌ 发送文件失败: {str(send_error)}")
            
            # 通知下载和发送完成
            try:
                message.edit_text("✅ 音频已发送！")
            except Exception as edit_error:
                logger.error(f"更新状态消息失败: {str(edit_error)}")
            
        finally:
            # 恢复原始代理设置
            logger.info("恢复原始代理设置")
            for proxy_var in ['NO_PROXY', 'no_proxy']:
                if proxy_var in os.environ:
                    del os.environ[proxy_var]
            
            for proxy_var, value in original_proxies.items():
                os.environ[proxy_var] = value
        
    except Exception as e:
        logger.error(f"处理YouTube链接时出错: {str(e)}", exc_info=True)
        try:
            message.edit_text(f"❌ 处理过程中出错: {str(e)}")
        except:
            update.message.reply_text(f"❌ 处理过程中出错: {str(e)}")

def handle_message(update: Update, context: CallbackContext) -> int:
    """处理用户消息"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    logger.info(f"收到来自用户 {user_id} 的消息: {text}")
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        logger.warning(f"用户 {user_id} 尝试访问，但不在允许列表中")
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return MAIN
    
    # 检查是否为YouTube链接
    if is_youtube_url(text):
        logger.info(f"检测到有效的YouTube链接: {text}")
        try:
            # 启动后台线程处理下载
            logger.info(f"创建下载线程处理链接: {text}")
            thread = threading.Thread(
                target=download_audio_in_thread,
                args=(update, context, text)
            )
            thread.daemon = True
            thread.start()
            logger.info(f"下载线程已启动: {thread.name}")
        except Exception as e:
            logger.error(f"创建下载线程时出错: {str(e)}", exc_info=True)
            update.message.reply_text(f"❌ 处理链接时出错: {str(e)}")
    else:
        logger.warning(f"收到无效链接: {text}")
        update.message.reply_text(
            "⚠️ 请发送有效的YouTube链接。\n\n"
            "示例:\n"
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://youtu.be/dQw4w9WgXcQ"
        )
    
    return MAIN

def cancel(update: Update, context: CallbackContext) -> int:
    """取消当前操作并返回主菜单"""
    update.message.reply_text("操作已取消，返回主菜单。")
    return MAIN

def error_handler(update, context):
    """处理错误"""
    logger.error(f"更新 {update} 导致错误 {context.error}")
    try:
        if update and update.effective_message:
            update.effective_message.reply_text("发生错误，请稍后重试。")
    except:
        pass

def main():
    """启动机器人"""
    # 检查是否设置了TOKEN
    if not TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN:
        logger.error("未设置TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN环境变量或配置")
        print("错误: 请在环境变量或配置文件中设置TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN")
        return 1
    
    logger.info(f"音频下载机器人启动中，使用Token: {TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN[:10]}...{TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN[-5:]}")
    logger.info(f"允许的用户: {TELEGRAM_ALLOWED_USERS}")
    logger.info(f"下载目录: {DOWNLOADS_DIR}")
    
    try:
        # 创建Updater和Dispatcher
        logger.info("创建Updater和Dispatcher")
        updater = Updater(TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # 设置命令菜单(显示在输入框左侧)
        logger.info("设置命令菜单")
        commands = [
            BotCommand("start", "启动机器人/返回主菜单"),
            BotCommand("help", "显示帮助信息")
        ]
        updater.bot.set_my_commands(commands)
        
        # 创建会话处理器
        logger.info("创建会话处理器")
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                MAIN: [
                    MessageHandler(Filters.text & ~Filters.command, handle_message),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # 添加处理器
        dispatcher.add_handler(conv_handler)
        dispatcher.add_handler(CommandHandler("help", help_command))
        
        # 添加错误处理器
        dispatcher.add_error_handler(error_handler)
        
        # 启动机器人
        logger.info("准备启动轮询...")
        
        # 首先删除webhook并清除任何待处理的更新
        logger.info("删除webhook并清除待处理的更新...")
        updater.bot.delete_webhook()
        
        # 启动轮询，明确设置drop_pending_updates=True
        logger.info("启动音频下载机器人轮询...")
        updater.start_polling(drop_pending_updates=True)
        logger.info("音频下载机器人轮询已启动")
        
        return updater  # 返回updater对象以便主程序控制
    
    except Exception as e:
        logger.error(f"启动机器人时出错: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    main().idle() 