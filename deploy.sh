#!/bin/bash
# YouTube视频处理助手 Docker部署脚本
# 用于在Mac mini上部署Telegram机器人Docker容器

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== YouTube视频处理助手 Docker部署脚本 =====${NC}"
echo "该脚本将帮助您在Docker上部署Telegram机器人服务"
echo

# 检查环境
echo -e "${YELLOW}[1/5] 检查环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装，请先安装Docker${NC}"
    echo "可以访问 https://docs.docker.com/desktop/install/mac-install/ 了解安装步骤"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose未安装${NC}"
    echo "从Docker Desktop 4.0.0开始，docker-compose命令已集成到docker compose中"
    echo "请尝试使用'docker compose'命令或安装最新的Docker Desktop"
    HAS_NEW_COMPOSE=true
else
    HAS_NEW_COMPOSE=false
fi

# 检查环境变量文件
echo -e "${YELLOW}[2/5] 检查配置文件...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "未找到.env文件，将从.env.example创建"
        echo "请在脚本完成后编辑.env文件，填入您的配置"
        cp .env.example .env
    else
        echo -e "${RED}错误: 未找到.env.example模板文件${NC}"
        exit 1
    fi
fi

# 确保配置目录存在
echo -e "${YELLOW}[3/5] 准备目录结构...${NC}"
mkdir -p audioprocess/transcription_results
mkdir -p audioprocess/downloads
mkdir -p audioprocess/temp_subtitles

# 构建Docker镜像
echo -e "${YELLOW}[4/5] 构建Docker镜像...${NC}"
if [ "$HAS_NEW_COMPOSE" = true ]; then
    docker compose build
else
    docker-compose build
fi

# 启动服务
echo -e "${YELLOW}[5/5] 启动Docker容器...${NC}"
if [ "$HAS_NEW_COMPOSE" = true ]; then
    docker compose up -d
else
    docker-compose up -d
fi

# 检查服务状态
echo -e "${GREEN}检查服务状态...${NC}"
if [ "$HAS_NEW_COMPOSE" = true ]; then
    docker compose ps
else
    docker-compose ps
fi

echo
echo -e "${GREEN}===== 部署完成 =====${NC}"
echo "YouTube视频处理助手Docker容器已成功部署"
echo 
echo -e "${YELLOW}提示:${NC}"
echo "1. 请确保已在.env文件中正确配置所有必需的参数"
echo "2. 请确保您的Mac mini保持启动状态，以便机器人能够持续响应"
echo "3. 查看日志: docker logs -f youtube-telegram-bot"
echo "4. 停止服务: $([ "$HAS_NEW_COMPOSE" = true ] && echo 'docker compose down' || echo 'docker-compose down')"
echo "5. 重启服务: $([ "$HAS_NEW_COMPOSE" = true ] && echo 'docker compose restart' || echo 'docker-compose restart')"
echo
echo "祝您使用愉快！" 