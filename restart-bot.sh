#!/bin/bash
# 重启YouTube视频处理助手Docker容器的脚本
# 用于系统启动时自动启动

# 等待网络连接和Docker启动
sleep 30

# 检查Docker是否运行
while ! docker info > /dev/null 2>&1; do
    echo "等待Docker启动..." >> ~/Library/Logs/youtube-telegram-bot.log
    sleep 10
done

# 进入项目目录
cd "$(dirname "$0")"

# 检查是否使用新版Docker Compose语法
if docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif docker-compose --version > /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "未找到Docker Compose命令" >> ~/Library/Logs/youtube-telegram-bot.log
    exit 1
fi

# 启动容器（如果未运行）
if ! $COMPOSE_CMD ps | grep -q "youtube-telegram-bot.*Up"; then
    echo "启动YouTube Telegram Bot容器..." >> ~/Library/Logs/youtube-telegram-bot.log
    $COMPOSE_CMD up -d
else
    echo "YouTube Telegram Bot容器已在运行" >> ~/Library/Logs/youtube-telegram-bot.log
fi 