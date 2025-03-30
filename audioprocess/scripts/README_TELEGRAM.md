# YouTube字幕摘要Telegram机器人

这个Telegram机器人可以接收YouTube视频链接，自动提取字幕或转录音频，然后生成内容摘要并发送给你。

## 功能特点

- 自动提取YouTube视频字幕（优先选择中文，其次英文）
- 若无字幕，自动下载音频并通过阿里云语音识别服务转录
- 使用大语言模型对字幕或转录内容生成摘要
- 实时显示处理日志，让你了解处理进度
- 支持用户权限控制，可限制特定用户使用

## 安装设置

### 前提条件

1. Python 3.6+
2. Telegram机器人Token（可从[@BotFather](https://t.me/BotFather)获取）
3. 你的Telegram用户ID（可从[@userinfobot](https://t.me/userinfobot)获取）

### 安装步骤

1. 运行安装脚本来设置Telegram机器人：

```bash
# 进入项目目录
cd audioprocess

# 运行安装脚本
python -m audioprocess.scripts.setup_telegram_bot
```

2. 按照提示输入你的Telegram Bot Token和允许使用的用户ID（逗号分隔）。

3. 安装脚本会自动创建启动脚本并安装所需依赖。

### 手动安装

如果自动安装失败，可以手动安装：

1. 安装依赖：

```bash
pip install python-telegram-bot==13.15
```

2. 在`audioprocess/config/settings.py`中添加或修改以下配置：

```python
# Telegram Bot配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "你的Bot Token")
TELEGRAM_ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
```

## 启动机器人

### 使用启动脚本

安装后会自动创建启动脚本：

- Linux/Mac: `audioprocess/scripts/start_telegram_bot.sh`
- Windows: `audioprocess\scripts\start_telegram_bot.bat`

### 手动启动

```bash
# 进入项目目录
cd audioprocess

# 启动机器人
python -m audioprocess.scripts.telegram_bot
```

## 使用方法

1. 在Telegram中打开你的机器人对话
2. 发送 `/start` 查看帮助信息
3. 直接发送一个YouTube视频链接
4. 机器人会自动开始处理，并实时更新处理日志
5. 完成后，机器人会发送提取的字幕或转录的内容摘要

## 故障排除

### 机器人无响应

- 检查Bot Token是否正确
- 确认机器人程序是否正在运行
- 检查日志输出查找错误信息

### 权限错误

- 确保你的用户ID已正确添加到允许用户列表
- 如果配置了`TELEGRAM_ALLOWED_USERS`，只有列表中的用户ID才能使用机器人

### 处理视频失败

- 检查YouTube链接是否有效
- 确认网络连接和代理设置
- 对于没有字幕的视频，确保阿里云转录服务配置正确

## 高级配置

可以在`audioprocess/config/settings.py`中调整以下参数：

- `TELEGRAM_BOT_TOKEN`: Telegram机器人的API Token
- `TELEGRAM_ALLOWED_USERS`: 允许使用机器人的用户ID列表（逗号分隔）

## 隐私与安全

- 机器人不会永久存储YouTube视频内容
- 处理结果仅发送给发起请求的用户
- 可以通过用户ID限制来控制机器人的访问权限 