#!/usr/bin/env python3
"""
音频下载机器人启动脚本
--------------------
单独启动音频下载功能机器人
"""

import os
import sys
import logging
import traceback
import threading
from telegram import Update, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)

# 将项目根目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from audioprocess.utils.youtube_utils import is_youtube_url, download_audio
from audioprocess.utils.proxy_manager import disable_proxies, restore_proxies
from audioprocess.config.settings import (
    TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN, 
    TELEGRAM_ALLOWED_USERS,
    DOWNLOADS_DIR
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('audio_bot.log')
    ]
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    """处理/start命令"""
    user_id = str(update.effective_user.id)
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    # 发送欢迎消息
    update.message.reply_text(
        "欢迎使用YouTube音频下载机器人！\n\n"
        "请发送YouTube链接，我将为您下载视频音频并发送给您。"
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """处理/help命令"""
    update.message.reply_text(
        "使用指南：\n\n"
        "直接发送YouTube视频链接，我将下载视频的音频文件并发送给您。\n\n"
        "命令：\n"
        "/start - 启动机器人/返回主菜单\n"
        "/help - 显示帮助信息\n"
        "/cancel - 取消当前操作"
    )

def cancel(update: Update, context: CallbackContext):
    """处理/cancel命令"""
    update.message.reply_text("操作已取消。")
    # 清除用户数据中可能存在的URL列表
    if 'youtube_urls' in context.user_data:
        del context.user_data['youtube_urls']

def error_handler(update, context):
    """处理错误"""
    logger.error(f"更新 {update} 导致错误 {context.error}")
    try:
        if update and update.effective_message:
            update.effective_message.reply_text("发生错误，请稍后重试。")
    except:
        pass

def handle_message(update: Update, context: CallbackContext):
    """处理用户消息"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    logger.info(f"收到来自用户 {user_id} 的消息: {text}")
    
    # 检查用户是否有权限使用机器人
    if TELEGRAM_ALLOWED_USERS and user_id not in TELEGRAM_ALLOWED_USERS:
        logger.warning(f"用户 {user_id} 尝试访问，但不在允许列表中")
        update.message.reply_text("抱歉，您没有权限使用此机器人。")
        return
    
    # 从文本中提取可能的YouTube链接
    import re
    youtube_pattern = r'(https?://)?((www\.)?youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    matches = re.findall(youtube_pattern, text)
    
    if matches:
        # 找到一个或多个YouTube链接
        extracted_urls = []
        for match in matches:
            # 重建完整URL
            full_url = f"https://www.youtube.com/watch?v={match[3]}" if "youtube.com" in match[1] else f"https://youtu.be/{match[3]}"
            extracted_urls.append(full_url)
        
        logger.info(f"从消息中提取到 {len(extracted_urls)} 个YouTube链接")
        
        if len(extracted_urls) == 1:
            # 只有一个链接，直接处理
            youtube_url = extracted_urls[0]
            logger.info(f"处理提取的链接: {youtube_url}")
            try:
                update.message.reply_text(f"⏳ 正在处理YouTube链接: {youtube_url}")
                thread = threading.Thread(
                    target=download_audio_in_thread,
                    args=(update, context, youtube_url)
                )
                thread.daemon = True
                thread.start()
                return
            except Exception as e:
                logger.error(f"创建下载线程时出错: {str(e)}", exc_info=True)
                update.message.reply_text(f"❌ 处理链接时出错: {str(e)}")
                return
        else:
            # 多个链接，让用户选择
            response = "我发现多个YouTube链接，请选择要下载的链接:\n\n"
            for i, url in enumerate(extracted_urls, 1):
                response += f"{i}. {url}\n"
            response += "\n请回复链接编号(1-{})来下载对应的音频。".format(len(extracted_urls))
            
            # 保存链接列表到用户数据中
            context.user_data['youtube_urls'] = extracted_urls
            
            update.message.reply_text(response)
            return
    
    # 检查是否为YouTube链接
    logger.info(f"正在检查链接是否为YouTube URL: {text}")
    youtube_url_check = is_youtube_url(text)
    logger.info(f"链接检查结果: {'是YouTube链接' if youtube_url_check else '不是YouTube链接'}")
    
    if youtube_url_check:
        logger.info(f"检测到有效的YouTube链接: {text}")
        try:
            # 启动后台线程处理下载
            logger.info(f"创建下载线程处理链接: {text}")
            update.message.reply_text("⏳ 收到链接，准备处理...", quote=True)
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
        # 检查是否是数字回复（选择之前提取的链接）
        if text.isdigit() and 'youtube_urls' in context.user_data:
            choice = int(text)
            urls = context.user_data['youtube_urls']
            
            if 1 <= choice <= len(urls):
                selected_url = urls[choice-1]
                logger.info(f"用户选择了链接 {choice}: {selected_url}")
                
                try:
                    update.message.reply_text(f"⏳ 正在处理所选YouTube链接: {selected_url}")
                    thread = threading.Thread(
                        target=download_audio_in_thread,
                        args=(update, context, selected_url)
                    )
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    logger.error(f"创建下载线程时出错: {str(e)}", exc_info=True)
                    update.message.reply_text(f"❌ 处理链接时出错: {str(e)}")
            else:
                update.message.reply_text(f"❌ 无效的选择。请选择1到{len(urls)}之间的数字。")
            
            return
        
        logger.warning(f"收到无效链接: {text}")
        update.message.reply_text(
            "⚠️ 请发送有效的YouTube链接。\n\n"
            "示例:\n"
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://youtu.be/dQw4w9WgXcQ"
        )

def download_audio_in_thread(update: Update, context: CallbackContext, youtube_url: str):
    """在线程中下载音频并发送给用户"""
    # 记录用户ID和消息ID，用于后续发送消息
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    
    try:
        # 发送处理中消息
        status_message = update.message.reply_text("⏳ 正在下载音频，请稍候...")
        
        # 下载音频 - 使用代理
        logger.info(f"开始从URL下载音频: {youtube_url}")
        
        # 检查URL是否有效
        if not is_youtube_url(youtube_url):
            logger.error(f"URL不是有效的YouTube链接: {youtube_url}")
            status_message.edit_text("❌ 无效的YouTube链接，请检查URL格式。")
            return
            
        # 执行下载
        audio_file = download_audio(youtube_url)
        
        # 检查下载是否成功
        if not audio_file:
            logger.error(f"下载失败: {youtube_url}")
            status_message.edit_text("❌ 音频下载失败。请检查链接或稍后重试。")
            return
            
        # 检查文件是否存在
        if not os.path.exists(audio_file):
            logger.error(f"下载的文件不存在: {audio_file}")
            status_message.edit_text("❌ 下载的文件不存在。请稍后重试。")
            return
            
        logger.info(f"下载完成: {audio_file}")
        logger.info(f"文件大小: {os.path.getsize(audio_file)/1024/1024:.2f} MB")
        
        # 在发送文件前禁用代理
        original_proxies = disable_proxies()
        
        try:
            # 发送音频文件
            logger.info(f"开始发送音频文件: {audio_file}")
            with open(audio_file, 'rb') as audio:
                status_message.edit_text("✅ 下载完成，正在发送音频文件...")
                context.bot.send_document(
                    chat_id=chat_id,
                    document=audio,
                    filename=os.path.basename(audio_file),
                    caption=f"🎵 已下载音频: {os.path.basename(audio_file)}"
                )
            logger.info(f"音频文件发送成功: {audio_file}")
            status_message.edit_text("✅ 音频文件已发送。")
        except Exception as send_error:
            logger.error(f"发送音频文件时出错: {str(send_error)}", exc_info=True)
            status_message.edit_text(f"❌ 发送音频文件时出错: {str(send_error)}")
        finally:
            # 恢复原始代理设置
            restore_proxies(original_proxies)
            
            # 尝试删除临时文件
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    logger.info(f"已删除临时文件: {audio_file}")
            except Exception as e:
                logger.error(f"删除临时文件时出错: {str(e)}")
        
    except Exception as e:
        logger.error(f"下载音频线程中出错: {str(e)}", exc_info=True)
        try:
            context.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=message_id,
                text=f"❌ 下载过程中出错: {str(e)}"
            )
        except:
            pass

def test_command(update: Update, context: CallbackContext) -> None:
    """处理/test命令，用于测试机器人是否响应"""
    user_id = str(update.effective_user.id)
    logger.info(f"收到来自用户 {user_id} 的测试命令")
    
    # 发送测试响应
    update.message.reply_text(
        "✅ 机器人正常运行中！\n\n"
        "您可以发送YouTube链接来下载音频。\n\n"
        "示例链接:\n"
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
        "https://youtu.be/dQw4w9WgXcQ"
    )

def main():
    """启动机器人"""
    # 检查是否设置了TOKEN
    if not TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN:
        logger.error("未设置TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN环境变量或配置")
        print("错误: 请在环境变量或配置文件中设置TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN")
        return 1
    
    # 确保下载目录存在
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    logger.info(f"音频下载机器人启动中，使用Token: {TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN[:10]}...{TELEGRAM_YOUTUBE_AUDIO_DOWNLOAD_BOT_TOKEN[-5:]}")
    logger.info(f"允许的用户ID列表: {TELEGRAM_ALLOWED_USERS}")
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
            BotCommand("help", "显示帮助信息"),
            BotCommand("test", "测试机器人是否正常响应")
        ]
        updater.bot.set_my_commands(commands)
        
        # 注册命令处理器
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("test", test_command))
        dispatcher.add_handler(CommandHandler("cancel", cancel))
        
        # 全局消息处理器 - 处理所有文本消息，不需要先使用/start
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        
        # 添加错误处理器
        dispatcher.add_error_handler(error_handler)
        
        # 先删除webhook以确保轮询模式可以工作
        logger.info("删除webhook...")
        updater.bot.delete_webhook()
        
        # 启动机器人
        logger.info("启动音频下载机器人轮询...")
        updater.start_polling(drop_pending_updates=True)
        logger.info("音频下载机器人已成功启动")
        logger.info("用户现在可以直接发送YouTube链接而无需先使用/start命令")
        
        # 保持运行
        updater.idle()
        
        return 0
        
    except Exception as e:
        logger.error(f"启动音频下载机器人时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 