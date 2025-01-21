# 语众不同 - 少数民族语言翻译、对话平台

## 项目简介

“语众不同”是一个结合 **LangChain** 和 **GPT** 模型的双语翻译工具。该平台提供翻译、生成教学资源、语音合成和对话等功能，帮助用户更好地翻译和使用少数民族语言。

## 功能

1. **翻译功能**：将少数民族语言文本翻译为主流语言。
2. **双语教材生成**：上传主流语言教材文件，生成少数民族语言版本，并将文件上传到数据库。
3. **语音合成功能**：将文本转换为语音，支持少数民族语言。
4. **对话模式**：使用少数民族语言与语言模型进行对话。
5. **数据统计**：展示各功能的使用情况统计。

## 目录结构

本仓库的文件结构如下：

```
|-- app.py              # Streamlit 前端代码
|-- backend.py          # FastAPI 后端代码
|-- ds_moremode.py      # DeepSeekAPI 相关代码
|-- gtts_sound.py       # 语音生成相关代码
|-- tencentdb.py        # 数据库表定义和连接
|-- 项目说明.pdf        # 项目说明文档
|-- 演示视频.mp4        # 演示视频
|-- README.md           # 仓库解释文件
|-- requirements.txt    # 项目所需环境
```

## 安装与运行

### 环境要求

```
# 基础依赖
streamlit==1.28.0
requests==2.31.0
pandas==2.1.1
openai==0.28.0
langchain==0.0.341

# 数据库相关
sqlalchemy==2.0.23
pymysql==1.1.0

# 语音合成
gtts==2.3.2

# FastAPI 相关
fastapi==0.103.1
uvicorn==0.23.2
python-multipart==0.0.6

# 其他工具
python-dotenv==1.0.0  # 用于管理环境变量
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置数据库

在 tencentdb.py 文件中配置您的数据库连接信息：

```bash
DATABASE_URL = "mysql+pymysql://<username>:<password>@<host>:<port>/<database>?charset=utf8mb4"
```

### 初始化数据库

运行 tencentdb.py 文件以创建数据库表

```bash
python tencentdb.py
```
### 运行后端服务

运行 backend.py 文件启动 FastAPI 后端服务：

```bash
uvicorn backend:app --host 127.0.0.1 --port 8000
```

### 运行前端应用

运行 app.py 文件启动 Streamlit 前端应用：

```bash
streamlit run app.py
```

## 使用说明

### 翻译功能

1. 在前端页面输入少数民族语言文本。
2. 点击“翻译为主流语言”按钮。
3. 查看翻译结果。

### 双语教材生成

1. 上传主流语言教材文件（支持 .txt 格式）。
2. 选择目标少数民族语言。
3. 点击“生成少数民族语言版本”按钮。
4. 查看生成的少数民族语言版本。
5. 点击“上传文件到数据库”按钮，将文件上传到数据库。

### 语音合成功能

1. 输入需要生成语音的文本。
2. 点击“生成语音”按钮。
3. 播放生成的语音。

### 对话模式

1. 输入少数民族语言问题。
2. 点击“发送消息”按钮。
3. 查看 GPT 模型的回答。

### 数据统计

1. 查看各功能的使用情况统计图表。

## 贡献

欢迎贡献代码和提出建议！请提交 Pull Request 或 Issue。