FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir python-telegram-bot==13.15 && \
    pip install --no-cache-dir httpx[socks]

# 创建必要的目录
RUN mkdir -p /app/audioprocess/transcription_results \
    /app/audioprocess/downloads \
    /app/audioprocess/temp_subtitles

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置容器启动命令
CMD ["python", "-m", "audioprocess.scripts.telegram_bot"] 