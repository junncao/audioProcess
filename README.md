# AudioProcess

一个用于从YouTube下载音频，提取字幕或转录音频内容，并进行文本摘要的工具包

## 功能特点

- **YouTube字幕提取**：优先尝试提取YouTube视频的字幕内容
- **音频下载和转录**：如果视频没有字幕，自动下载音频并转录
- **文本摘要生成**：对提取的字幕或转录内容进行摘要总结
- **多种输入支持**：支持YouTube URL、OSS音频URL或直接文本输入
- **模块化设计**：代码结构清晰，易于维护和扩展
- **代理管理**：内置代理管理功能，便于在不同网络环境下使用

## 安装

### 方法一：直接使用

```bash
# 克隆仓库
git clone <仓库地址>
cd audioprocess

# 安装依赖
pip install -r requirements.txt
```

### 方法二：作为包安装

```bash
# 克隆仓库
git clone <仓库地址>
cd audioprocess

# 安装为包
pip install -e .
```

## 配置

在使用前，需要配置以下环境变量或修改`audioprocess/config/settings.py`文件：

```bash
# 阿里云OSS配置
export OSS_ACCESS_KEY_ID="你的OSS_ACCESS_KEY_ID"
export OSS_ACCESS_KEY_SECRET="你的OSS_ACCESS_KEY_SECRET"

# 阿里云DashScope配置
export DASHSCOPE_API_KEY="你的DASHSCOPE_API_KEY"
```

## 使用方法

### 1. 处理YouTube视频

```bash
# 从YouTube视频中提取字幕或下载音频并转录，然后生成摘要
python run.py --url "https://www.youtube.com/watch?v=视频ID"

# 强制使用音频下载和转录流程，跳过字幕提取
python run.py --url "https://www.youtube.com/watch?v=视频ID" --force-audio

# 跳过摘要生成步骤
python run.py --url "https://www.youtube.com/watch?v=视频ID" --skip-summary

# 使用代理
python run.py --url "https://www.youtube.com/watch?v=视频ID" --youtube-proxy "http://127.0.0.1:7890"
```

### 2. 直接处理OSS音频URL

```bash
# 使用OSS音频URL进行转录和摘要
python run.py --oss-url "https://你的存储桶.oss-cn-shanghai.aliyuncs.com/你的音频文件.mp3"
```

### 3. 直接生成文本摘要

```bash
# 从命令行输入文本进行摘要
python run.py --text "需要摘要的文本内容"

# 从文件读取文本进行摘要
python run.py --text-file 文本文件路径.txt
```

### 4. 禁用代理

```bash
# 禁用所有代理设置
python run.py --url "https://www.youtube.com/watch?v=视频ID" --no-proxy
```

## 测试模块

在`tests`目录下提供了各个功能的独立测试脚本：

```bash
# 测试字幕提取功能
python tests/test_extract_subtitle.py --url "https://www.youtube.com/watch?v=视频ID"

# 测试YouTube音频下载功能
python tests/test_youtube_download.py --url "https://www.youtube.com/watch?v=视频ID"

# 测试OSS上传功能
python tests/test_oss_upload.py --file 本地音频文件路径

# 测试音频转录功能
python tests/test_transcribe.py --url 音频文件URL

# 测试文本摘要功能
python tests/test_summarize.py --text "需要摘要的文本内容"
```

## 目录结构

```
audioprocess/
├── audioprocess/
│   ├── __init__.py
│   ├── main.py              # 主程序文件
│   │   └── __init__.py
│   ├── config/              # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py      # 配置项
│   ├── core/                # 核心功能模块
│   │   ├── __init__.py
│   │   ├── youtube_downloader.py  # YouTube音频下载
│   │   ├── subtitle_extractor.py  # 字幕提取
│   │   ├── oss_uploader.py        # OSS上传
│   │   ├── transcription.py       # 音频转录
│   │   └── summarization.py       # 文本摘要
│   └── utils/               # 工具模块
│       ├── __init__.py
│       ├── logger.py        # 日志工具
│       ├── proxy_manager.py # 代理管理
│       └── file_utils.py    # 文件处理工具
├── tests/                   # 测试模块
│   ├── test_youtube_download.py
│   ├── test_oss_upload.py
│   ├── test_transcribe.py
│   └── test_summarize.py
├── run.py                   # 入口点脚本
├── setup.py                 # 安装配置
└── README.md                # 说明文档
```

## 注意事项

1. 确保有足够的网络连接速度，以便下载YouTube视频。
2. 阿里云OSS和DashScope API需要有效的账户和密钥。
3. 某些地区访问YouTube可能需要使用代理。
4. 音频转录和摘要生成可能需要一定的处理时间。
5. 如果使用SOCKS代理，请确保安装了`httpx[socks]`：`pip install httpx[socks]`。

## 许可证

[MIT](LICENSE) 