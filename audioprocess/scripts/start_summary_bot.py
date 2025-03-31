#!/usr/bin/env python3
"""
字幕摘要机器人启动脚本
--------------------
单独启动字幕摘要功能机器人
"""

import os
import sys
import logging
import traceback
import threading
from telegram import Update, ParseMode, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext
)

# 将项目根目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from audioprocess.utils.youtube_utils import is_youtube_url, extract_youtube_subtitles
from audioprocess.utils.proxy_manager import disable_proxies, restore_proxies
from audioprocess.main import process_youtube_video
from audioprocess.config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, 
    TRANSCRIPTION_RESULTS_DIR, TEMP_SUBTITLES_DIR
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('summary_bot.log')
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
    
    # 创建按钮
    keyboard = [
        [KeyboardButton("字幕摘要")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # 发送欢迎消息
    update.message.reply_text(
        "欢迎使用YouTube字幕摘要机器人！\n\n"
        "我可以帮您从YouTube视频中提取字幕并生成摘要。\n\n"
        "请直接发送YouTube链接，我将为您提取视频字幕并生成摘要。",
        reply_markup=reply_markup
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """处理/help命令"""
    update.message.reply_text(
        "使用指南：\n\n"
        "直接发送YouTube链接，我将提取视频字幕并生成摘要。\n\n"
        "命令：\n"
        "/start - 启动机器人/显示菜单\n"
        "/help - 显示帮助信息\n"
        "/test - 测试机器人是否正常响应"
    )

def test_command(update: Update, context: CallbackContext) -> None:
    """处理/test命令，用于测试机器人是否响应"""
    user_id = str(update.effective_user.id)
    logger.info(f"收到来自用户 {user_id} 的测试命令")
    
    # 发送测试响应
    update.message.reply_text(
        "✅ 字幕摘要机器人正常运行中！\n\n"
        "您可以发送YouTube链接来获取视频字幕摘要。\n\n"
        "示例链接:\n"
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
        "https://youtu.be/dQw4w9WgXcQ"
    )

def cancel(update: Update, context: CallbackContext):
    """处理/cancel命令"""
    update.message.reply_text("操作已取消。")
    # 清除可能存在的上下文数据
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
    
    # 处理按钮点击
    if text == "字幕摘要":
        update.message.reply_text(
            "请发送YouTube链接，我将提取视频字幕并生成摘要。"
        )
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
                    target=process_youtube_in_thread,
                    args=(update, context, youtube_url)
                )
                thread.daemon = True
                thread.start()
                return
            except Exception as e:
                logger.error(f"创建处理线程时出错: {str(e)}", exc_info=True)
                update.message.reply_text(f"❌ 处理链接时出错: {str(e)}")
                return
        else:
            # 多个链接，让用户选择
            response = "我发现多个YouTube链接，请选择要处理的链接:\n\n"
            for i, url in enumerate(extracted_urls, 1):
                response += f"{i}. {url}\n"
            response += "\n请回复链接编号(1-{})来选择要处理的视频。".format(len(extracted_urls))
            
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
            # 启动线程处理YouTube视频
            logger.info(f"创建线程处理链接: {text}")
            update.message.reply_text("⏳ 收到链接，准备处理...", quote=True)
            thread = threading.Thread(
                target=process_youtube_in_thread,
                args=(update, context, text)
            )
            thread.daemon = True
            thread.start()
            logger.info(f"处理线程已启动: {thread.name}")
        except Exception as e:
            logger.error(f"创建处理线程时出错: {str(e)}", exc_info=True)
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
                        target=process_youtube_in_thread,
                        args=(update, context, selected_url)
                    )
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    logger.error(f"创建处理线程时出错: {str(e)}", exc_info=True)
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

def process_youtube_in_thread(update: Update, context: CallbackContext, youtube_url: str):
    """在线程中处理YouTube视频"""
    try:
        # 发送处理中消息
        message = update.message.reply_text("⏳ 正在处理YouTube视频，请稍候...")
        
        # 禁用代理，处理完成后恢复
        original_proxies = disable_proxies()
        
        try:
            # 处理YouTube视频，获取字幕和摘要
            result = process_youtube_video(youtube_url, force_audio=False)
            
            if result['success']:
                # 成功获取字幕和摘要
                if 'summary' in result:
                    # 有摘要
                    message.edit_text(
                        f"✅ 视频摘要:\n\n{result['summary']}",
                        parse_mode=ParseMode.HTML
                    )
                elif 'text' in result:
                    # 有字幕但没有摘要
                    # 只显示前300个字符
                    text = result['text'][:300] + ("..." if len(result['text']) > 300 else "")
                    message.edit_text(
                        f"✅ 已提取字幕:\n\n{text}\n\n⚠️ 未能生成摘要。",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    # 未知情况
                    message.edit_text("❌ 处理视频时出现未知错误。")
            else:
                # 处理失败
                error_msg = result.get('error', '未知错误')
                message.edit_text(f"❌ 处理视频时出错: {error_msg}")
                
        except Exception as e:
            logger.error(f"处理YouTube视频时出错: {str(e)}", exc_info=True)
            message.edit_text(f"❌ 处理视频时出错: {str(e)}")
        finally:
            # 恢复原来的代理设置
            restore_proxies(original_proxies)
            
    except Exception as e:
        logger.error(f"YouTube处理线程中出错: {str(e)}", exc_info=True)
        try:
            update.message.reply_text(f"❌ 处理过程中出错: {str(e)}")
        except:
            pass

def main():
    """启动机器人"""
    # 检查是否设置了TOKEN
    if not TELEGRAM_BOT_TOKEN:
        logger.error("未设置TELEGRAM_BOT_TOKEN环境变量或配置")
        print("错误: 请在环境变量或配置文件中设置TELEGRAM_BOT_TOKEN")
        return 1
    
    # 确保必要目录存在
    os.makedirs(TRANSCRIPTION_RESULTS_DIR, exist_ok=True)
    os.makedirs(TEMP_SUBTITLES_DIR, exist_ok=True)
    
    logger.info(f"字幕摘要机器人启动中，使用Token: {TELEGRAM_BOT_TOKEN[:8]}...{TELEGRAM_BOT_TOKEN[-5:]}")
    logger.info(f"允许的用户ID列表: {TELEGRAM_ALLOWED_USERS}")
    
    try:
        # 创建Updater和Dispatcher
        updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # 设置命令菜单(显示在输入框左侧)
        commands = [
            BotCommand("start", "启动机器人/显示菜单"),
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
        updater.bot.delete_webhook()
        
        # 启动机器人
        logger.info("启动字幕摘要机器人轮询...")
        updater.start_polling(drop_pending_updates=True)
        logger.info("字幕摘要机器人已成功启动")
        logger.info("用户现在可以直接发送YouTube链接而无需先使用/start命令")
        
        # 保持运行
        updater.idle()
        
        return 0
        
    except Exception as e:
        logger.error(f"启动字幕摘要机器人时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 