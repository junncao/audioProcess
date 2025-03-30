# YouTube视频处理助手

一个功能丰富的Telegram机器人，可以处理YouTube视频，提取字幕，生成摘要，下载音频，以及进行AI对话。

## 功能特点

### 📝 字幕摘要功能
- 自动提取YouTube视频字幕（优先中文，其次英文）
- 若无字幕，自动下载音频并通过阿里云语音识别服务转录
- 使用大语言模型对字幕或转录内容生成摘要
- 发送摘要内容和完整结果文件

### 🎵 音频下载功能
- 从YouTube视频中提取高质量WebM音频
- 直接将音频文件发送至Telegram

### 🤖 AI对话功能
- 与阿里云大模型进行自然语言对话
- 保持对话上下文，实现连续交流
- 自动避免代理问题，确保稳定连接

### 其他特性
- 实时显示处理日志，让你了解处理进度
- 支持用户权限控制，可限制特定用户使用
- 三种便捷的交互方式：
  - Telegram命令菜单（聊天框左侧）
  - 自定义键盘按钮（聊天框底部）
  - 直接发送YouTube链接

## 安装设置

### 前提条件

1. Python 3.6+
2. Telegram机器人Token（可从[@BotFather](https://t.me/BotFather)获取）
3. 你的Telegram用户ID（可从[@userinfobot](https://t.me/userinfobot)获取）
4. 阿里云账号（用于DashScope API和OSS服务）

### 安装步骤

1. 克隆或下载本项目

2. 安装依赖：
```bash
# 安装基本依赖
pip install -r requirements.txt

# 安装Telegram机器人依赖
pip install python-telegram-bot==13.15
```

3. 设置配置：
```bash
# 运行Telegram机器人设置脚本
python -m audioprocess.scripts.setup_telegram_bot
```
按照提示输入你的Telegram Bot Token和允许使用的用户ID。

4. 设置阿里云服务：
   - 在`audioprocess/config/settings.py`中配置OSS和DashScope相关参数
   - 确保`DASHSCOPE_API_KEY`、`OSS_ACCESS_KEY_ID`和`OSS_ACCESS_KEY_SECRET`已正确设置

## 使用方法

### 启动机器人

有多种方式可以启动机器人：

```bash
# 方式1：从项目根目录启动
python telegram_bot.py

# 方式2：使用模块启动
python -m audioprocess.scripts.telegram_bot

# 方式3：使用脚本启动（Mac/Linux）
./audioprocess/scripts/start_telegram_bot.sh

# 方式3：使用脚本启动（Windows）
audioprocess\scripts\start_telegram_bot.bat
```

### 使用机器人

1. 在Telegram中打开你的机器人对话
2. 使用下方的按钮菜单或左侧命令菜单选择功能：
   - 📝 **字幕摘要**：`/summary` - 提取字幕并生成摘要
   - 🎵 **音频下载**：`/download` - 下载音频文件
   - 🤖 **AI对话**：`/chat` - 与AI模型对话
3. 或直接发送YouTube链接（默认使用字幕摘要功能）

#### 字幕摘要模式
1. 选择字幕摘要功能或直接发送YouTube链接
2. 机器人会显示处理进度和日志
3. 完成后，你将收到：
   - 字幕或转录文本的摘要
   - 包含完整内容的文件

#### 音频下载模式
1. 选择音频下载功能
2. 发送YouTube链接
3. 机器人会下载并发送音频文件

#### AI对话模式
1. 选择AI对话功能
2. 直接发送消息，与阿里云大模型对话
3. 使用`/exit`退出对话模式

## 配置选项

主要配置文件位于`audioprocess/config/settings.py`，包含以下选项：

### Telegram相关
- `TELEGRAM_BOT_TOKEN`: 机器人的API Token
- `TELEGRAM_ALLOWED_USERS`: 允许使用机器人的用户ID列表

### 阿里云相关
- `OSS_ENDPOINT`, `OSS_REGION`, `OSS_BUCKET_NAME`: OSS存储配置
- `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`: OSS访问凭证
- `DASHSCOPE_API_KEY`: 阿里云DashScope API密钥

### 路径相关
- `RESULTS_DIR`: 结果保存目录
- `TEMP_DIR`: 临时文件目录
- `DOWNLOADS_DIR`: 下载文件目录

## 代理管理

机器人采用智能代理管理策略，确保各功能正常工作：

- **YouTube下载**：使用系统代理，确保能访问YouTube
- **阿里云API调用**：禁用代理，避免SOCKS代理错误
- **Telegram通信**：自动管理代理设置

## 故障排除

### 问题：无法启动机器人
- 检查`TELEGRAM_BOT_TOKEN`是否正确设置
- 确认python-telegram-bot版本为13.x
- 检查网络连接

### 问题：字幕提取或转录失败
- 检查阿里云DashScope API密钥是否有效
- 确认OSS配置正确
- 验证YouTube链接有效性

### 问题："Using SOCKS proxy"错误
- 此问题已自动处理，代码会禁用AI对话和文件发送时的代理

### 问题：没有收到结果文件
- 检查文件大小是否超过Telegram限制
- 查看日志中的错误信息
- 检查`RESULTS_DIR`目录中是否有生成的文件

## 清理空目录

使用以下命令清理项目中的空目录：

```bash
python cleanup_empty_dirs.py
```

## 贡献和支持

欢迎提交Issue和Pull Request。如有使用问题，请提供详细的错误日志和复现步骤。 