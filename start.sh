#!/bin/bash
# 启动脚本：同时启动音频下载机器人和文本摘要机器人

# 设置工作目录和Python路径
export PYTHONPATH=$(pwd)

# 创建日志目录
mkdir -p logs
export $(grep -v '^#' .env | xargs)
# 记录启动时间
echo "=== 机器人启动于 $(date) ===" > terminal_logs.txt

# 启动音频下载机器人
echo "正在启动音频下载机器人..." >> terminal_logs.txt
nohup python3 -m audioprocess.scripts.start_audio_bot >> terminal_logs.txt 2>&1 &
AUDIO_BOT_PID=$!
echo "音频下载机器人已启动，PID: $AUDIO_BOT_PID" >> terminal_logs.txt

# 等待2秒，确保第一个机器人已完全初始化
sleep 2

# 启动文本摘要机器人
echo "正在启动文本摘要机器人..." >> terminal_logs.txt
nohup python3 -m audioprocess.scripts.start_summary_bot >> terminal_logs.txt 2>&1 &
SUMMARY_BOT_PID=$!
echo "文本摘要机器人已启动，PID: $SUMMARY_BOT_PID" >> terminal_logs.txt

# 记录进程ID便于以后停止
echo "PID列表：" >> terminal_logs.txt
echo "音频下载机器人: $AUDIO_BOT_PID" >> terminal_logs.txt
echo "文本摘要机器人: $SUMMARY_BOT_PID" >> terminal_logs.txt

# 将PID保存到文件中，方便以后终止进程
echo "$AUDIO_BOT_PID $SUMMARY_BOT_PID" > bot_pids.txt

echo "两个机器人都已在后台启动，所有日志将输出到 terminal_logs.txt"
echo "可以使用以下命令查看日志："
echo "  tail -f terminal_logs.txt"
echo "可以使用以下命令停止机器人："
echo "  kill \$(cat bot_pids.txt)"