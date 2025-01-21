import streamlit as st
import requests
import pandas as pd
import os
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.llms import OpenAI

# 设置页面标题、图标和布局
st.set_page_config(page_title="语众不同", page_icon="🌍", layout="wide")

# 添加自定义CSS样式
def add_background_and_styles():
    st.markdown("""
        <style>
            body {
                background: linear-gradient(135deg, #f4a6a6, #a8c0e9);  /* 红蓝渐变，低饱和度 */
                font-family: 'Arial', sans-serif;
                color: #333;
                margin: 0;
                padding: 0;
            }

            /* 标题样式 */
            .title {
                font-size: 36px;
                color: #4A90E2;
                text-align: center;
                margin-top: 20px;
                text-shadow: 1px 1px 4px #000000;
                font-family: Source Han Sans;
                font-weight: 600; /* 中等粗细 */
            }

            /* 侧边栏样式 */
            .sidebar-title {
                font-size: 20px;
                color: #4A90E2;
                margin-bottom: 10px;
            }

            /* 简洁的输入框和按钮 */
            .stSelectbox, .stRadio, .stTextArea, .stButton, .stFileUploader {
                background-color: transparent;
                border: none;
                margin-bottom: 20px;
            }

            /* 页面内容区域 */
            .stTextArea textarea {
                font-size: 16px;
                padding: 10px;
                width: 100%;
                border: none;
                resize: vertical;
                background-color: transparent;
            }

            /* 按钮样式 */
            .stButton button {
                background-color: #4A90E2;
                color: #fff;
                font-size: 16px;
                padding: 12px;
                border-radius: 5px;
                border: none;
                cursor: pointer;
                width: 300px;
            }
            .stButton button:hover {
                background-color: #3d85c6;
                color: #f0f0f0;  /* 改成浅灰色 */
            }

            /* 提示框样式 */
            .stWarning, .stSuccess, .stError {
                background-color: transparent;
                color: #333;
                padding: 15px;
                margin-bottom: 20px;
                border-left: 4px solid;
            }

            .stError {
                border-left-color: #FF4C4C;
            }

            .stSuccess {
                border-left-color: #39B54A;
            }

            .stWarning {
                border-left-color: #FFCC00;
            }

            /* 输入框样式 */
            .stTextArea textarea {
                font-size: 16px;
                padding: 10px;
                width: 100%;
                background-color: transparent;
                border: none;
            }

            /* 上传文件样式 */
            .stFileUploader input {
                border-radius: 5px;
                padding: 12px;
                background-color: transparent;
                border: none;
                width: 100%;
            }

            /* 图标和按钮对齐 */
            .stButton, .stTextArea, .stSelectbox {
                margin-bottom: 20px;
            }

            /* 页面结构对齐 */
            .stMarkdown hr {
                border: 0;
                border-top: 1px solid #ddd;
                margin: 30px 0;
            }

            .stRadio label, .stSelectbox label {
                font-size: 18px;
                color: #4A90E2;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

# 应用样式和背景
add_background_and_styles()

# **页面标题**
st.markdown('<h1 class="title">“语”众不同</h1>', unsafe_allow_html=True)

# **初始模式选择**
st.sidebar.markdown('<h3 class="sidebar-title">模式选择</h3>', unsafe_allow_html=True)
mode = st.sidebar.radio("请选择使用模式：", ["教学模式", "对话模式"])

# **对话模式**
if mode == "对话模式":
    st.subheader("对话模式")
    st.markdown("在这里，您可以使用少数民族语言进行对话。")

    # 初始化对话历史记录
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    # 输入框：用户输入
    user_message = st.text_area("点击此处开始对话😊", height=100)

    # 提交按钮
    if st.button("发送消息"):
        if user_message.strip():
            # 将用户输入添加到对话历史记录
            st.session_state.conversation_history.append({"role": "user", "message": user_message})

            # 构建请求数据，包含历史对话记录
            request_data = {
                "message": user_message,
                "lang": "minority",
                "history": st.session_state.conversation_history
            }

            # 模拟与 GPT 对话服务（实际需要后端 API）
            response = requests.post(
                "http://127.0.0.1:8000/chat",  # 替换为实际 GPT 对话后端 API 地址
                json=request_data
            )
            if response.status_code == 200:
                gpt_response = response.json().get("response", "对话失败")
                # 将模型回答添加到对话历史记录
                st.session_state.conversation_history.append({"role": "model", "message": gpt_response})

                st.success("模型回答：")
                st.write(gpt_response)
            else:
                st.error("对话服务调用失败，请检查后端服务是否正常运行。")
        else:
            st.warning("请输入问题后再点击发送消息。")

    # 显示往期问答
    st.subheader("往期问答记录")
    for entry in st.session_state.conversation_history:
        if entry["role"] == "user":
            st.markdown(f"**您:** {entry['message']}")
        else:
            st.markdown(f"**模型:** {entry['message']}")


# **教学模式**
else:
    st.subheader("教学模式")
    st.markdown("""
    这是一个结合 **LangChain** 和 **GPT** 模型的双语教育工具，旨在保护少数民族语言。
    您可以进行翻译、生成教学资源，并使用语音合成功能。
    """)

    # 添加分隔线
    st.markdown("<hr>", unsafe_allow_html=True)

    # **功能 1：翻译**
    st.markdown("### 翻译功能")
    user_input = st.text_area("请输入少数民族语言文本：", height=100)

    if st.button("翻译为主流语言"):
        if user_input.strip():
            response = requests.post(
                "http://127.0.0.1:8000/translate",  # 替换为实际后端 API 地址
                json={"text": user_input, "source_lang": "minority", "target_lang": "mainstream"}
            )
            if response.status_code == 200:
                translation = response.json().get("translation", "翻译失败")
                st.success("翻译结果：")
                st.write(translation)
            else:
                st.error("翻译服务调用失败，请检查后端服务是否正常运行。")
        else:
            st.warning("请输入文本以进行翻译。")

    # 添加分隔线
    st.markdown("<hr>", unsafe_allow_html=True)

    # **功能 2：双语教材生成**
    st.markdown("### 教学资源生成")
    uploaded_file = st.file_uploader("上传主流语言教材文件（支持 .txt）", type=["txt"])

    # 添加目标语言选择
    minority_languages = ["哈萨克语", "朝鲜语", "维吾尔语", "藏语", "蒙古语"]  # 可扩展的少数民族语言列表
    language_map = {
    "哈萨克语": "ru",
    "朝鲜语": "ko",
    "蒙古语": "kk",
    "维吾尔语": "ug",
    "藏语": "bo",
    }

    selected_language_1 = st.selectbox("请选择目标少数民族语言：", minority_languages, key="selectbox1")

    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        st.text_area("上传的文件内容", content, height=200)

        if st.button("生成少数民族语言版本"):
            if selected_language_1:
                response = requests.post(
                    "http://127.0.0.1:8000/generate",  # 替换为实际 API 地址
                    json={"content": content, "target_lang": selected_language_1}
                )
                if response.status_code == 200:
                    generated_content = response.json().get("generated_text", "生成失败")
                    st.success("生成的少数民族语言版本：")
                    st.text_area("生成内容", generated_content, height=200)
                else:
                    st.error("生成服务调用失败，请检查后端服务。")
            else:
                st.warning("请选择目标少数民族语言。")
    
        # 上传文件到数据库
        if st.button("上传文件到数据库"):
            response = requests.post(
                "http://127.0.0.1:8000/upload_txt",
                files={"file": uploaded_file},
                data={"file_name": uploaded_file.name}
            )
            if response.status_code == 200:
                st.success("文件上传成功！")
            else:
                st.error("文件上传失败，请检查后端服务。")
   

    # 添加分隔线
    st.markdown("<hr>", unsafe_allow_html=True)

    # **功能 3：语音合成**
    st.markdown("### 语音合成功能")
    speech_input = st.text_area("请输入需要生成语音的文本：", height=100)
    
    selected_language_2 = st.selectbox("请选择目标少数民族语言：", minority_languages, key="selectbox2")

    if st.button("生成语音"):
        if speech_input.strip():
            lang_code = language_map.get(selected_language_2, "mn")  # 默认选择蒙古语（'mn'）

            response = requests.post(
                "http://127.0.0.1:8000/synthesize",  # 替换为实际 API 地址
                json={"text": speech_input, "lang": lang_code}  # 替换为实际语言代码
            )
            if response.status_code == 200:
                # if "audio_content" in response.json():
                    # audio_file = "output_audio.mp3"
                    # with open(audio_file, "wb") as f:
                    #     f.write(response.content)

                    # 展示音频播放器
                st.audio(response.content, format="audio/mp3")
                st.success("语音生成成功！")
                # else:
                #     st.error(response.json().get("error", "语音生成失败"))
            else:
                st.error("语音合成失败，请检查后端服务。")
        else:
            st.warning("请输入中文文本以生成少数民族语音。")

    # 添加分隔线
    st.markdown("<hr>", unsafe_allow_html=True)

    # **功能 4：数据统计**
    st.markdown("### 使用情况统计")

    # 向后端请求数据统计信息
    response = requests.get("http://127.0.0.1:8000/usage_stats")
    if response.status_code == 200:
        stats = response.json()
        data = {
            "功能": [stat["feature"] for stat in stats],
            "使用次数": [stat["count"] for stat in stats],
        }
        df = pd.DataFrame(data)
        st.bar_chart(df.set_index("功能"))
    else:
        st.error("无法获取数据统计信息，请检查后端服务。")