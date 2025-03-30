# Docker部署指南 - YouTube视频处理助手

本文档介绍如何在Mac mini上使用Docker部署YouTube视频处理助手，以实现全天候运行的Telegram机器人服务。

## 部署前提

1. Mac mini已安装MacOS
2. 已安装[Docker Desktop](https://www.docker.com/products/docker-desktop/)
3. 基本的命令行操作知识

## 快速部署

我们提供了一键部署脚本，只需几个简单步骤即可完成部署：

1. 克隆或下载本项目到Mac mini
2. 打开终端，进入项目目录
3. 给部署脚本添加执行权限并运行：

```bash
chmod +x deploy.sh
./deploy.sh
```

4. 按照提示编辑`.env`文件，填入您的配置信息：

```bash
nano .env  # 或使用任何文本编辑器
```

5. 重新启动容器以应用配置：

```bash
docker compose restart  # 或 docker-compose restart
```

## 配置详解

`.env`文件包含所有服务配置，请确保正确设置以下参数：

```
# Telegram配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here  # 从BotFather获取
TELEGRAM_ALLOWED_USERS=your_telegram_user_id      # 从userinfobot获取

# 阿里云OSS配置
OSS_ACCESS_KEY_ID=your_oss_access_key_id
OSS_ACCESS_KEY_SECRET=your_oss_access_key_secret
OSS_BUCKET_NAME=your_oss_bucket_name
OSS_ENDPOINT=your_oss_endpoint
OSS_REGION=your_oss_region

# 阿里云DashScope配置
DASHSCOPE_API_KEY=your_dashscope_api_key

# 代理配置（可选）
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

## 设置开机自启

确保Mac mini重启后服务自动运行，请按照以下步骤设置：

1. 编辑`start-on-boot.plist`文件，替换YOUR_USERNAME为您的系统用户名：

```bash
nano start-on-boot.plist
```

2. 将文件复制到LaunchAgents目录：

```bash
cp start-on-boot.plist ~/Library/LaunchAgents/com.youtube.telegrambot.starter.plist
```

3. 加载启动项：

```bash
chmod +x restart-bot.sh
launchctl load ~/Library/LaunchAgents/com.youtube.telegrambot.starter.plist
```

## 常用操作

### 管理容器

```bash
# 查看容器状态
docker ps

# 查看容器日志
docker logs -f youtube-telegram-bot

# 停止服务
docker compose down  # 或 docker-compose down

# 重启服务
docker compose restart  # 或 docker-compose restart

# 重新构建并启动服务
docker compose up -d --build  # 或 docker-compose up -d --build
```

### 解决常见问题

1. 如果容器无法启动，请检查日志：

```bash
docker logs youtube-telegram-bot
```

2. 如果配置有误，编辑`.env`文件后重启容器：

```bash
nano .env
docker compose restart  # 或 docker-compose restart
```

3. 如果代理设置有问题，您可以编辑`.env`文件调整代理配置。

4. 如果需要完全重置，可以删除容器和镜像后重新部署：

```bash
docker compose down  # 或 docker-compose down
docker rmi youtube-telegram-bot
./deploy.sh
```

## 高级配置

### 持久化存储

Docker配置已设置以下目录的持久化存储：

- `./audioprocess/transcription_results`: 转录和摘要结果
- `./audioprocess/downloads`: 下载的音频文件
- `./audioprocess/temp_subtitles`: 临时字幕文件
- `./audioprocess/config`: 配置文件

这些目录的数据会保存在Mac mini本地，容器重启后不会丢失。

### 日志管理

Docker容器的日志配置为保留最近3个10MB的日志文件，可在`docker-compose.yml`中调整：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 系统资源配置

如需限制容器资源使用，可在`docker-compose.yml`中添加以下配置：

```yaml
services:
  telegram-bot:
    # 其他配置...
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

## 常见错误排查

| 错误 | 可能原因 | 解决方法 |
|------|---------|---------|
| 容器启动失败 | 配置文件错误 | 检查`.env`文件和`docker-compose.yml` |
| API调用失败 | 阿里云密钥无效 | 更新`.env`中的阿里云配置 |
| 网络错误 | 代理配置问题 | 检查或禁用代理设置 |
| 文件无法保存 | 权限问题 | 检查目录权限，确保用户有写入权限 |
| 内存不足 | 系统资源受限 | 增加Docker可用内存或减少容器资源限制 |

## 安全注意事项

1. 请勿将包含API密钥的`.env`文件共享给他人
2. 定期检查日志文件，确保没有异常访问
3. 确保您的Mac mini使用防火墙并定期更新系统

## 更新服务

当有新版本发布时，更新服务的步骤：

1. 拉取最新代码：

```bash
git pull
```

2. 重新构建并启动容器：

```bash
docker compose up -d --build  # 或 docker-compose up -d --build
``` 