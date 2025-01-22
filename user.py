import os
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
import streamlit as st
import streamlit_authenticator as stauth
from neo4j import GraphDatabase
from dotenv import load_dotenv
from DBtest import WordWiseDB
import pandas as pd
import re
from chains import load_llm
import time
import uuid

load_dotenv(".env")

url = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM")
os.environ["NEO4J_URL"] = url


llm = load_llm(llm_name, config={"ollama_base_url": ollama_base_url})
memory = ConversationBufferMemory(return_messages=True)
conversation = ConversationChain(llm=llm,memory=memory)

# 初始化 Neo4j 数据库实例
db = WordWiseDB(uri=url, user=username, password=password)

def create_wordlist():
    """创建新词单"""
    if 'uid' not in st.session_state:
        st.error("请先登录以创建词单")
        return
    
    st.title("创建新词单")
    
    # 选择词单难度
    difficulty = st.selectbox("选择难度", ["CET6", "自定义文件上传"])  # 选择CET6或上传文件
    
    name = st.text_input("词单名称")
    description = st.text_area("词单描述")
    
    if difficulty == "自定义文件上传":
        file = st.file_uploader("上传词汇文件", type=["txt", "csv"])
    else:
        file = None  # CET6时不需要上传文件
    
    if st.button("创建词单"):
        if name and description:
            with st.spinner("正在创建词单..."):
                wordlist_id = str(uuid.uuid4())  # 使用uuid生成唯一的词单ID
                db.create_wordlist(wid=wordlist_id, name=name, description=description, owner_uid=st.session_state['uid'])
                
                # 如果选择了CET6难度，自动导入CET6词汇
                if difficulty == "CET6":
                    cet6_file_path = "/app/CET_4_6_edited.txt"  
                    if os.path.exists(cet6_file_path):
                        with open(cet6_file_path, "r", encoding="utf-8") as f:
                            words = f.readlines()
                        
                        # 将CET6词汇添加到词单
                        for word in words:
                            db.add_word_to_list(word.strip(), wordlist_id)
                        
                        st.success(f"词单创建成功！词单 ID: {wordlist_id}，已导入CET6词汇！")
                    else:
                        st.error(f"未找到CET6词汇文件，请确保路径正确：{cet6_file_path}")
                
                # 如果选择自定义文件上传，则读取上传的文件
                elif difficulty == "自定义文件上传" and file is not None:
                    file_contents = file.getvalue().decode("utf-8")  # 获取文件内容
                    
                    if file.name.endswith(".txt"):
                        words = file_contents.splitlines()  # 按行分割
                    
                    elif file.name.endswith(".csv"):
                        df = pd.read_csv(file)
                        words = df.iloc[:, 0].tolist()  # 获取第一列数据为单词
                    
                    # 添加词汇到词单
                    for word in words:
                        db.add_word_to_list(word.strip(), wordlist_id)
                    
                    st.success(f"词单创建成功！词单 ID: {wordlist_id}，已导入文件中的词汇！")
                else:
                    st.error("请选择文件并上传")
        else:
            st.error("请填写词单名称和描述")



def add_word_to_wordlist():
    """向词单添加单词"""
    st.title("向词单添加单词")
    
    # 获取当前用户的所有词单
    if 'uid' not in st.session_state:
        st.error("请先登录！")
        return
    
    wordlists = db.get_user_wordlists(st.session_state['uid'])  # 获取用户的所有词单
    if not wordlists:
        st.error("您没有任何词单，请先添加词单！")
        return
    
    # 显示词单选择框（用户选择词单名称）
    wordlist_options = [wl['name'] for wl in wordlists]
    selected_wordlist_name = st.selectbox("请选择词单", wordlist_options)
    
    # 获取选中的词单ID
    selected_wordlist_id = next(wl['wordlist_id'] for wl in wordlists if wl['name'] == selected_wordlist_name)
    
    word_text = st.text_input("单词")
    
    if st.button("添加单词"):
        if word_text:
            # 添加单词到选中的词单
            db.add_word_to_list(word_text, selected_wordlist_id)
            st.success(f"单词 '{word_text}' 添加成功到 '{selected_wordlist_name}' 词单")
        else:
            st.error("请填写单词")

def wordlist_selection():
    """让用户选择学习的词单"""
    if 'uid' not in st.session_state:
        st.error("请先登录！")
        return

    # 从数据库获取用户的所有词单
    wordlists = db.get_user_wordlists(st.session_state['uid'])  # 假设该方法返回用户的所有词单
    if not wordlists:
        st.error("您没有任何词单，请先添加词单！")
        return

    # 显示词单选择框
    wordlist_options = [(wl['name'], wl['wordlist_id']) for wl in wordlists]
    selection = st.selectbox("请选择词单", 
                           options=wordlist_options,
                           format_func=lambda x: x[0],
                           key='wordlist_selector')
    
    # 只有当用户确实选择了词单才继续
    if selection:
        selected_wordlist_name, selected_wordlist_id = selection
        
        # 保存选中的词单ID
        st.session_state['wordlist_id'] = selected_wordlist_id
        st.success(f"您选择了词单：{selected_wordlist_name}")

        # 进入学习模式
        word_learning()

def chat_with_llm(user_input, current_word=None):
    """与LLM对话的功能"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # 构建上下文提示
    if current_word:
        context = f"当前学习的单词是: {current_word}。"
        prompt = context + user_input
    else:
        prompt = user_input
    
    # 获取LLM回答
    response = llm.predict(prompt)
    
    # 保存对话历史
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    return response

def generate_contextual_quiz(word, llm):
    """生成英文例句并手动替换单词为下划线"""
    prompt = f"""Generate a simple English sentence using the word "{word}". Make sure it shows proper usage of the word."""
    
    sentence = llm.predict(prompt).strip()
    # 手动替换单词为下划线 (忽略大小写)
    quiz_sentence = re.sub(word, "_____", sentence, flags=re.IGNORECASE)
    return sentence, quiz_sentence

def check_contextual_answer(original_sentence, word, user_answer, llm):
    """评判用户答案是否合适"""
    prompt = f"""Context: Original sentence: {original_sentence}
    Original word: {word}
    User's word: {user_answer}
    
    请用中文分析:
    1. 用户的答案在句子中是否语法正确
    2. 用户的答案在语义上是否合适
    3. 与原单词相比,用户的答案是否更好或存在什么问题
    4. 给出改进建议"""
    
    return llm.predict(prompt)

def word_learning():
    """单词学习"""
    st.title("单词学习")

    # 创建两列布局
    col1, col2 = st.columns([0.7, 0.3])

    with col1:
        # 如果没有选择词单，先让用户选择
        if 'wordlist_id' not in st.session_state:
            wordlist_selection()
            return

        # 如果没有选择学习方式，显示选择学习方式的界面
        if 'learning_option' not in st.session_state:
            st.session_state.learning_option = st.selectbox("请选择学习方式", 
                                                        [ "语境化学习", "单词拼写", "中译英", "英译中",])

        # 如果当前单词没有加载，则加载一个新的单词
        if 'current_word' not in st.session_state or not st.session_state.current_word:
            word = db.get_random_word(st.session_state['uid'], st.session_state['wordlist_id'])
            st.session_state.current_word = word
            st.session_state.question_answered = False  # 标记是否已回答当前问题

        word = st.session_state.current_word

        if word:
            # 根据不同学习方式使用不同的展示逻辑
            if st.session_state.learning_option == "单词拼写":
                quiz = generate_spelling_quiz(word, llm)
                question, options, answer = extract_quiz_details(quiz)
                display_question_and_check_answer(question, options, word)  # 调用公共函数

            elif st.session_state.learning_option == "中译英":
                quiz = generate_translation_quiz(word, llm)
                question, options, answer = extract_quiz_details(quiz)
                display_question_and_check_answer(question, options, answer, input_type="radio")  # 使用选择题

            elif st.session_state.learning_option == "英译中":
                quiz = generate_definitions_quiz(word, llm)
                question, options, answer = extract_quiz_details(quiz)
                display_question_and_check_answer(question, options, answer, input_type="radio")  # 使用选择题

            elif st.session_state.learning_option == "语境化学习":
                # 生成例句和题目
                original_sentence, quiz_sentence = generate_contextual_quiz(word, llm)
                
                st.write("### 当前单词:", word)
                st.info("🔍 请根据句子上下文，在横线处填入合适的单词:")
                st.write(quiz_sentence)
                
                # 用户输入
                user_answer = st.text_input("你的答案:")
                
                # 提交评判
                if st.button("提交"):
                    if user_answer:
                        # 获取详细评判
                        feedback = check_contextual_answer(original_sentence, word, user_answer, llm)
                        st.write("### 评判结果:")
                        st.write(feedback)
                        st.session_state.question_answered = True
                    else:
                        st.warning("请输入答案!")

            # 提交答案后才显示“下一个”按钮
            if st.session_state.question_answered:
                if st.button("➡️ 下一个"):
                    # 获取新的单词
                    word = db.get_random_word(st.session_state['uid'], st.session_state['wordlist_id'])
                    st.session_state.current_word = word
                    st.session_state.question_answered = False  # 重置问题标记
                    # 不要递归调用 word_learning()，这样可以避免重复渲染的问题

            # 添加“结束学习”按钮，点击后结束当前学习
            if st.button("结束学习"):
                st.session_state.learning_option = None  # 清空学习方式
                st.session_state.current_word = None  # 清空当前单词
                st.session_state.current_meaning = None  # 清空当前单词解释
                st.write("学习已结束。感谢您的努力！")

        else:
            st.error("没有找到单词，可能是数据库为空。")


    with col2:
        st.markdown("### 🤖 AI助手")
        
        # 简化的聊天功能
        user_input = st.text_input("在这里输入你的问题...")
        if st.button("发送"):
            if user_input:
                # 构建带有当前单词上下文的提示
                if st.session_state.get('current_word'):
                    context = f"当前学习的单词是: {st.session_state.current_word}。"
                    prompt = context + user_input
                else:
                    prompt = user_input
                
                # 获取回答并显示
                response = llm.predict(prompt)
                st.write("🤖: " + response)


def display_question_and_check_answer(question, options, answer, input_type="text"):
    """显示题目并检查用户的答案"""
    st.write(question)
    
    # 使用唯一的key来防止重复
    input_key = f"text_input_{st.session_state.current_word}"  # 使用当前单词作为key的一部分
    
    # 根据输入类型，显示相应的输入框
    if input_type == "radio":
        user_answer = st.radio("请选择答案", options.keys())
    else:
        user_answer = st.text_input("请输入答案：", key=input_key)  # 使用唯一的key

    # 提交按钮
    submit_button = st.button(label="提交答案")
    
    # 判断用户是否点击了提交按钮
    if submit_button:
        if user_answer:  # 确保用户输入了答案
            if user_answer.lower() == answer.lower():  # 忽略大小写
                st.success("回答正确！")
            else:
                st.error(f"回答错误！正确答案是：{answer}")
            st.session_state.question_answered = True  # 标记已回答问题
        else:
            st.warning("请输入答案！")
    
    return user_answer



def generate_spelling_quiz(word, llm):
    """生成单词拼写题目"""
    prompt = f"""请为以下英语单词生成一个拼写题：
    单词: {word}
    请提供该单词的拼写题目，格式如下：
    题目: 拼写单词：[单词中文释义]，[单词词性]
    答案: [正确拼写]"""
    
    spelling_quiz = llm.predict(prompt)
    
    return spelling_quiz


def generate_translation_quiz(word, llm):
    """生成中译英选择题"""
    prompt = f"""请为以下英语单词生成一个中译英的选择题：
    单词: {word}
    题目: [单词的中文释义]：请选择正确的英文翻译:
    A. [选项A]
    B. [选项B]
    C. [选项C]
    D. [选项D]
    答案: [正确选项]"""
    
    translation_quiz = llm.predict(prompt)

    return translation_quiz


def generate_definitions_quiz(word, llm):
    """生成英译中选择题"""
    prompt = f"""请为以下英语单词生成一个中文释义选择题：
    单词: {word}
    题目: [单词本身]：请选择正确的释义：
    A. [选项A]
    B. [选项B]
    C. [选项C]
    D. [选项D]
    答案: [正确选项]"""
    
    definitions_quiz = llm.predict(prompt)

    return definitions_quiz

def extract_quiz_details(quiz_content):
    """从生成的题目内容中提取出题目、选项和答案"""
    
    # 提取题目
    question_pattern = r"题目[:：]\s*(.*?)(?=\n(?:A|B|C|D|答案)|$)"  # 提取题目部分，直到选项或答案，支持无选项情况
    question_match = re.search(question_pattern, quiz_content)
    
    # 提取选项
    options_pattern = r"([A-D])\.\s*(.*?)(?=\n[A-D]|答案|$)"  # 提取选项部分
    options_match = re.findall(options_pattern, quiz_content)
    
    # 提取答案
    answer_pattern = r"答案[:：]\s*([A-D])"  # 提取答案
    answer_match = re.search(answer_pattern, quiz_content)
    
    if question_match:
        question = question_match.group(1).strip()  # 提取题目
    else:
        question = None
        
    if options_match:
        options = {option[0]: option[1].strip() for option in options_match}  # 提取选项并转为字典形式
    else:
        options = None
    
    if answer_match:
        answer = answer_match.group(1).strip()  # 提取答案
    else:
        answer = None
    
    return question, options, answer

def check_in():
    """打卡功能"""
    st.title("打卡")
    
    streak, total = db.check_in(st.session_state['uid'])
    st.write(f"连续打卡天数：{streak} 天")
    st.write(f"总学习天数：{total} 天")

def show_user_stats():
    """显示用户统计信息"""
    st.title("学习统计")
    
    stats = db.get_user_stats(st.session_state['uid'])
    st.write(f"连续打卡天数：{stats['streak_days']} 天")
    st.write(f"总学习天数：{stats['total_study_days']} 天")
    st.write(f"已掌握单词数：{stats['mastered_words']}")
    st.write(f"主题颜色：{stats['theme_color']}")
    st.write(f"提醒时间：{stats['reminder_time']}")
    st.write(f"学习目标：{stats['study_goal']}")


def auth_page():
    """统一的认证页面"""
    st.markdown(
        """
        <style>
        .auth-container {
            max-width: 400px;
            margin: 4rem auto;
            padding: 2.5rem;
            background: white;
            border-radius: 15px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        }
        
        .auth-title {
            color: #2e7bcf;
            text-align: center;
            font-size: 2.2rem;
            font-weight: bold;
            margin-bottom: 2rem;
        }
        
        .auth-link {
            text-align: center;
            margin-top: 1rem;
            color: #6c757d;
        }
        
        .auth-link a {
            color: #2e7bcf;
            text-decoration: none;
            cursor: pointer;
        }
        
        .auth-link a:hover {
            text-decoration: underline;
        }
        
        .form-input {
            margin-bottom: 1rem;
        }
        
        .stButton > button {
            width: 100%;
            background: #2e7bcf;
            color: white;
            padding: 0.8rem;
            font-size: 1.1rem;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            margin-top: 1rem;
            transition: all 0.3s;
        }
        
        .stButton > button:hover {
            background: #236bb3;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    #st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    # Logo
    st.markdown("""
        <h1 class="auth-title">
            <span style="margin-right:10px">🎯</span>WordWise
        </h1>
    """, unsafe_allow_html=True)
    
    # 初始化模式
    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = "login"
    
    # 登录界面
    if st.session_state.auth_mode == "login":
        with st.form("login_form"):
            account = st.text_input("账号", placeholder="请输入账号")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            if st.form_submit_button("登 录", use_container_width=True):
                if account and password:
                    user_info = db.get_user_by_account(account)
                    if user_info and user_info['password'] == password:
                        st.success("登录成功！")
                        st.balloons()
                        return user_info['uid']
                    else:
                        st.error("账号或密码错误")
                else:
                    st.warning("请填写账号和密码")
        
        # 注册链接
        # st.markdown("""
        #     <div class="auth-link">
        #         没有账号？<a href="#" onclick="document.dispatchEvent(new CustomEvent('register'))">立即注册</a>
        #     </div>
        # """, unsafe_allow_html=True)
        
        if st.button("切换到注册", key="to_register"):
            st.session_state.auth_mode = "register"
            st.rerun()
    
    # 注册界面
    else:
        with st.form("register_form"):
            account = st.text_input("账号", placeholder="请输入账号")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            email = st.text_input("邮箱", placeholder="请输入邮箱")
            
            if st.form_submit_button("注 册", use_container_width=True):
                if account and password and email:
                    uid = db.create_user(account, password, email, "")
                    st.success("注册成功！")
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error("请填写所有必填项")
        
        # 返回登录链接
        # st.markdown("""
        #     <div class="auth-link">
        #         已有账号？<a href="#" onclick="document.dispatchEvent(new CustomEvent('login'))">返回登录</a>
        #     </div>
        # """, unsafe_allow_html=True)
        
        if st.button("返回登录", key="to_login"):
            st.session_state.auth_mode = "login"
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    return None

# 主页面逻辑
def main():
    """主页面，控制页面显示逻辑"""
    # 初始化页面状态
    if 'current_page' not in st.session_state:
        st.session_state.current_page = None
        
    # 自定义样式
    st.markdown(
        """
        <style>
        .auth-container {
            max-width: 400px;
            margin: 2rem auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .auth-title {
            color: #2e7bcf;
            text-align: center;
            font-size: 2rem;
            margin-bottom: 2rem;
        }
        
        .auth-switch {
            text-align: center;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 2rem;
        }
        
        .auth-switch button {
            background: none;
            border: none;
            color: #6c757d;
            padding: 0.5rem 1rem;
            margin: 0 0.5rem;
            cursor: pointer;
            border-radius: 5px;
        }
        
        .auth-switch button.active {
            background: #2e7bcf;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    if 'uid' not in st.session_state:
        uid = auth_page()
        if uid:
            st.session_state['uid'] = uid

    else:
        st.sidebar.markdown(
            """
            <style>
            /* 整体容器内边距 */
            section[data-testid="stSidebar"] > div {
                padding: 1rem;
            }
            
            /* 标题样式 */
            .sidebar-title {
                font-size: 1.5rem;
                font-weight: bold;
                color: #1E90FF;
                margin-bottom: 1.5rem;
                text-align: center;
            }
            
            /* 按钮容器样式 */
            .stButton {
                margin: 0.8rem 0;
            }
            
            /* 按钮样式 */
            .stButton > button {
                background: white !important;
                border: 2px solid #1E90FF !important;
                color: #1E90FF !important;
                padding: 1.5rem !important;
                font-size: 1.1rem !important;
                font-weight: 500 !important;
                border-radius: 12px !important;
                width: 100% !important;
                min-height: 80px !important;
                transition: all 0.3s ease !important;
                margin: 0.5rem 0 !important;
                box-shadow: 0 2px 5px rgba(30,144,255,0.1) !important;
            }
            
            /* 按钮悬停效果 */
            .stButton > button:hover {
                background: #1E90FF !important;
                color: white !important;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(30,144,255,0.2) !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.sidebar.markdown("<h1 class='sidebar-title'>🎯 学习中心</h1>", unsafe_allow_html=True)

        # 菜单选项
        if st.sidebar.button("📝 创建词单", key="create", use_container_width=True):
            st.session_state.current_page = "create_wordlist"
            
        if st.sidebar.button("➕ 添加单词", key="add", use_container_width=True):
            st.session_state.current_page = "add_word_to_wordlist"
            
        if st.sidebar.button("📚 开始学习", key="learn", use_container_width=True):
            st.session_state.current_page = "start_learning"
            
        if st.sidebar.button("📅 每日打卡", key="checkin", use_container_width=True):
            st.session_state.current_page = "daily_checkin"
            
        if st.sidebar.button("📊 学习统计", key="stats", use_container_width=True):
            st.session_state.current_page = "show_stats"
        
        # 根据当前页面状态显示内容
        if st.session_state.current_page == "create_wordlist":
            create_wordlist()
        elif st.session_state.current_page == "add_word_to_wordlist":
            add_word_to_wordlist()
        elif st.session_state.current_page == "start_learning":
            wordlist_selection()
        elif st.session_state.current_page == "daily_checkin":
            check_in()
        elif st.session_state.current_page == "show_stats":
            show_user_stats()

if __name__ == "__main__":
    main()