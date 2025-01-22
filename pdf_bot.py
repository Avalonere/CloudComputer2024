import os
import re

from collections import Counter
import streamlit as st
from PyPDF2 import PdfReader
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

from DBtest import WordWiseDB
from chains import load_llm
from dotenv import load_dotenv

from sqlite import exec_query
import nltk
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from nltk.corpus import wordnet
import time
from streamlit_modal import Modal
import requests

from docx import Document
import hashlib

#加载环境变量
load_dotenv(".env")
ollama_base_url = os.getenv("OLLAMA_BASE_URL")
llm_name = os.getenv("LLM")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_usr = os.getenv("NEO4J_USERNAME")
neo4j_passwd = os.getenv("NEO4J_PASSWORD")
#连接neo4j数据库
db = WordWiseDB(uri=neo4j_uri, user=neo4j_usr, password=neo4j_passwd)


class StreamHandler(BaseCallbackHandler):
    """创建新的单词列表

            Args:
                wid (str): 词单唯一标识符
                name (str): 词单名称
                description (str): 词单描述
                owner_uid (str): 创建者的用户ID

            Note:
                会建立用户与词单之间的 OWNS 关系
            """
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text
        self.complete_text = ""

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.complete_text += token

    def get_text(self):
        return self.complete_text


llm = load_llm(llm_name, config={"ollama_base_url": ollama_base_url})
memory = ConversationBufferMemory(return_messages=True)
conversation = ConversationChain(llm=llm, memory=memory)
st.set_page_config(page_title="PDF词汇学习助手", layout="wide")





def ReadLinesAsList(file):
    """读取单词表文件中的单词

    因为文件每行只有一个单词，读取每一行的内容并去除空格，
    然后放入字典中。

            Args:
               file:文件路径

            Returns:
                vocab:文件中单词组成的字典
    """
    with open(file, 'r') as f:
        lines = f.readlines()
        vocab = {word.strip().split()[0].lower()
                 for word in lines if word.strip()}

        return vocab


# 预加载词汇表
@st.cache_data
def load_vocab_tables():
    """预加载CET6和COCA词汇表"""

    cet6_path = "/app/CET_4_6_edited.txt"
    coca_path = "/app/COCA_20000.txt"

    #从文件中读取单词表
    cet6_vocab = ReadLinesAsList(cet6_path)
    coca_vocab = ReadLinesAsList(coca_path)

    return cet6_vocab, coca_vocab


# 加载词汇表，存储到全局变量里
CET6_VOCAB, COCA_VOCAB = load_vocab_tables()
wnl = WordNetLemmatizer()





def get_word_category(tag):
    #根据tag判断词性
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.VERB


def is_valid_word(word):
    """检查是否为有效单词"""
    word = word.lower()
    # 过滤专有名词和非COCA词表单词
    if not word in COCA_VOCAB or not word.isalpha():
        # 必须全是字母
        return False

    return True


def extract_words(text):
    """提取并处理文本中的单词"""
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    valid_words = []
    for word in words:
        if len(word) > 1:  # 过滤单字母
            # 词形还原
            if is_valid_word(word):
                valid_words.append(wnl.lemmatize(word, get_word_category(pos_tag([word])[0][1])))
    return valid_words


def display_word_card(word, explanation, freq, index, total,support_add):
    """显示单词卡片"""

    #定义样式
    st.markdown("""
    <style>
    .word-card {
        padding: 20px;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        #显示单词、频次、释义
        st.markdown(f"<div class='word-card'>", unsafe_allow_html=True)
        st.markdown(f"### {word}")
        st.caption(f"在文档中出现 {freq} 次")
        st.markdown(explanation)
        st.caption(f"卡片 {index + 1}/{total}")
        st.markdown("</div>", unsafe_allow_html=True)


        if support_add:

            col1 , col2 = st.columns([2,1])
            with col1:
                # 从选择框中选择已创建的单词表
                option = st.selectbox("选择单词表", ["CET6"]) 
                

            with col2:
                st.write("")
                st.write("")
                # 点击按钮，根据选择的单词表name，在session_state中查询对应单词表的id
                if st.button("加入生词库"):
                    if option is not None:
                        #将单词加入指定id的单词表中
                        st.success("添加成功！✅")





def get_word_explanations(words, llm):
    """使用LLM生成单词释义"""
    explanations = {}
    prompt_template = """请为以下英语单词提供简明的中文释义和一个简短的例句:
    单词: {word}
    要求:
    1. 给出最常用的1-2个含义
    2. 提供一个简单的例句
    3. 输出格式:
       释义: [中文释义]
       例句: [英文例句]"""

    for word in words:
        container = st.empty()
        stream_handler = StreamHandler(container)
        prompt = prompt_template.format(word=word)
        llm.predict(prompt, callbacks=[stream_handler])
        explanations[word] = stream_handler.get_text()
        container.empty()  # 清除临时显示
    return explanations

def get_doc_difficulty(text,llm):
    """使用LLM分析文档难度"""
    prompt_template = """请从词汇和语法的角度分析下面这篇英语文档的阅读难度：
    文档:{text}
    """
    container = st.empty()
    stream_handler = StreamHandler(container)
    prompt =prompt_template.format(text=text)
    llm.predict(prompt,callbacks=[stream_handler])
    container.empty()

    return stream_handler.get_text()

def get_hashValue(text):
    """计算文本的哈希值

        Args:
            text(str):文本

        Returns:
            hash_value(str):文本哈希值的16进值字符串
        """
    hash_object = hashlib.sha256(text.encode())
    hash_value = hash_object.hexdigest()
    return hash_value

def ask_doc_questions(text,llm,question):
    """使用LLM回答与文档相关的问题"""
    prompt_template = """请根据文档回答以下相关问题：
       文档:{text}
       问题:{question}
       """
    container = st.empty()
    stream_handler = StreamHandler(container)
    prompt = prompt_template.format(text=text,question=question)
    llm.predict(prompt, callbacks=[stream_handler])
    container.empty()
    return stream_handler.get_text()



def main():

    '''将一些关键的状态存储在session_state中并进行初始化：
    - explanations:当前文档生词的释义
    - word_freq:当前文档中所有单词的频率
    - current_word_index:当前单词卡片正在显示的单词的下标
    - unknown_words_list:当前文档中超出认知范围的单词
    - qa_hash:当前文档的文本哈希值，用于在文档问题回答中区分新旧文档
    - df_hash:当前文档的文本哈希值，用于在文档难度分析中区分不同文档
    - question:当前用户提出的与文档相关的问题
    - difficulty:当前文档的难度分析
    - upload_file:当前用户上传的文档文件】
    - file_uploaded:用户是否上传了新文档
    '''

    if "explanations" not in st.session_state:
        st.session_state.explanations = {}
    if "word_freq" not in st.session_state:
        st.session_state.word_freq = None
    if "current_word_index" not in st.session_state:
        st.session_state.current_word_index = 0
    if "unknown_words_list" not in st.session_state:
        st.session_state.unknown_words_list = []
    if "qa_hash" not in st.session_state:
        st.session_state.qa_hash=None
    if "df_hash" not in st.session_state:
        st.session_state.df_hash=None
    if "question" not in st.session_state:
        st.session_state.question=None
    if "answer" not in st.session_state:
        st.session_state.answer=None
    if "difficulty" not in st.session_state:
        st.session_state.difficulty=None

    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file=None

    st.title("📚 PDF词汇学习助手")
    st.markdown("""
    这是一个帮助你提升英语词汇量的工具:
    1. 上传英语PDF文档
    2. 选择你的词汇水平
    3. 获取超出你词汇水平的单词解释和例句
    """)

    st.divider()

   #一个文件上传组件，允许上传pdf或docx
    file = st.file_uploader("上传英语PDF文档", type=["pdf","docx"],key="file_uploader")


    text=""
    #如果文件上传组件中存在一个文件
    if file is not None:
        #检查这个文件是否是新上传的，如果是则更新session_state中的状态，判定用户上传了新文件
        if file != st.session_state.uploaded_file:
            st.session_state.uploaded_file = file
            st.session_state.file_uploaded = True
        #否则判定用户未上传新的文件
        else:
            st.session_state.file_uploaded = False


    else:
        st.session_state.file_uploaded = False

    # 根据用户上传文件的文件名，采用相应的方法读取文件，得到文件内容字符串text
    if st.session_state.uploaded_file is not None:
        cur_file = st.session_state.uploaded_file
        if cur_file.name.endswith("pdf"):

            with st.spinner('正在分析文档...'):
                # 读取PDF
                pdf_reader = PdfReader(cur_file)

                for page in pdf_reader.pages:
                    text += page.extract_text()

        elif cur_file.name.endswith("docx"):

            with st.spinner('正在分析文档...'):
                # 读取PDF
                doc = Document(cur_file)

                for para in doc.paragraphs:
                    text += para.text + "\n"

    #提取text中的有效的单词words
    words = extract_words(text)
    st.session_state.word_freq = Counter(words)
    #找出words中超出范围的单词
    unknown_words = {word for word in st.session_state.word_freq.keys()
                        if word not in CET6_VOCAB}

    #当unknown_words不为空
    if unknown_words:
        #且当前文档文件是新上传的
        if st.session_state.file_uploaded:
            with st.spinner('正在生成单词释义...'):
                #为unknown_words中的单词生成释义，存储在session_state中
                st.session_state.explanations = get_word_explanations(unknown_words, llm)
                st.session_state.unknown_words_list = sorted(unknown_words)


        #并列放置三个导航按钮用于遍历unknown_words
        col1, col2, col3 = st.columns(3)
        #通过修改状态中的current_word_index，实现点击按钮显示上一个或下一个单词
        with col1:
            if st.button("⬅️ 上一个"):
                st.session_state.current_word_index = (st.session_state.current_word_index - 1) % len(
                    st.session_state.unknown_words_list)
        with col2:
            if st.button("➡️ 下一个"):
                st.session_state.current_word_index = (st.session_state.current_word_index + 1) % len(
                    st.session_state.unknown_words_list)
        with col3:
            if st.button("🔄 重置"):
                st.session_state.current_word_index = 0

        # 从缓存中获取当前单词下标并显示当前单词卡片
        if st.session_state.current_word_index>=len(st.session_state.unknown_words_list):
            st.session_state.current_word_index=0
        current_word = st.session_state.unknown_words_list[st.session_state.current_word_index]
        display_word_card(
            current_word,
            st.session_state.explanations[current_word],
            st.session_state.word_freq[current_word],
            st.session_state.current_word_index,
            len(st.session_state.unknown_words_list),
            True
        )

    st.divider()
    difficulty_btn = st.button("分析文档阅读难度")
    #如果当前文档文本不为空
    if len(text)>0:
        if difficulty_btn:
            #点击按钮后，比较session_state中的文本哈希值与当前文本的哈希值，判断两个文本是否一致
            if not (get_hashValue(text) == st.session_state.df_hash and st.session_state.difficulty):
                #当两个文本不一致或session_state中的难度分析未生成时，需要重新生成难度分析
                with st.spinner('正在分析文档难度...'):
                    difficulty =get_doc_difficulty(text,llm)
                    st.session_state.difficulty=difficulty
                    st.session_state.df_hash = get_hashValue(text)
                #否则，直接显示已有的难度分析
        if get_hashValue(text) == st.session_state.df_hash and st.session_state.difficulty:
            st.markdown(st.session_state.difficulty)



    st.divider()

    input_container = st.empty()
    #一个文本输入框用于输入问题
    user_input = input_container.text_input("提问与文档相关的问题",key="text_input",)
    if st.session_state.file_uploaded:
        #当新上传一个文件时，将输入框清空
        user_input = input_container.text_input("提问与文档相关的问题",key="text_input_empty",value='')
    if len(text)>0:
        #如果当前文本不为空
        if len(user_input)>0:
            #如果当前输入的问题和session_state中保存问题一致，当前文本的哈希值与session_state中保存的文本哈希值一致且session_state中已有答案
            if user_input == st.session_state.question and st.session_state.answer and get_hashValue(text)==st.session_state.qa_hash:
                #直接显示session_state缓存的答案
                st.write(st.session_state.question)
                st.write(st.session_state.answer)
            else:
                #否则重新生成答案，并更新session_state
                with st.spinner('正在思考文档问题...'):
                    st.session_state.question = user_input
                    response = ask_doc_questions(text,question=user_input,llm=llm)
                    st.session_state.answer=response
                    st.session_state.qa_hash=get_hashValue(text)
                    #st.write(st.session_state.question)
                    st.write(st.session_state.answer)



def recall_new_words():
    if "current_recall_word_index" not in st.session_state:
        st.session_state.current_recall_word_index = 0

    num_words = st.session_state.num_new_words
    st.header("需要复习的生词:{}".format(num_words))

    query_sql = "SELECT word , explanations FROM new_words ORDER BY insert_time LIMIT ?"

    res = exec_query(query_sql, (num_words,))
    new_words = []
    explanations = {}

    for row in res:
        new_words.append(row[0])
        explanations[row[0]] = row[1]


    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ 上一个"):
            st.session_state.current_recall_word_index = (st.session_state.current_recall_word_index - 1) % len(
                new_words)
    with col2:
        if st.button("➡️ 下一个"):
            print("下一个:{}".format(st.session_state.current_recall_word_index))
            st.session_state.current_recall_word_index = (st.session_state.current_recall_word_index + 1) % len(
                new_words)
    with col3:
        if st.button("🔄 重置"):
            st.session_state.current_recall_word_index = 0

    # 从缓存中获取并显示当前单词卡片
    if st.session_state.current_word_index >= len(new_words):
        st.session_state.current_word_index = 0
    current_word = new_words[st.session_state.current_recall_word_index]
    display_word_card(
        current_word,
        explanations[current_word],
        1,
        st.session_state.current_recall_word_index,
        len(new_words),
        False
    )




if __name__ == "__main__":

    if "page" not in st.session_state:
        st.session_state.page = "PDF"

    if "num_new_words" not in st.session_state:
        st.session_state.num_new_words = 0
    #初始化session_state中关于用户uid和用户单词表的状态
    if "word_lists" not in st.session_state:
        st.session_state.word_lists={}
    #从url中读取传入的用户uid
    params = st.query_params
    if "uid" in params:
        st.session_state.uid = params['uid'][0]
        #从数据库中查询用户创建的单词表
        word_lists=db.get_user_wordlists(params['uid'][0])
        #将单词表存储在session_state的字典中，以单词表的name为键，以单词表的id为值
        for word_list in word_lists:
            st.session_state.word_lists[word_list["name"]] = word_list["wordlist_id"]



    interval = 1
    main_container = st.empty()
    modal = Modal(key="modal_Key", title="警告")
    page = st.selectbox("选择功能", ["PDF", "复习单词"])

    if page == "PDF":
        st.session_state.page = "PDF"
    elif page == "复习单词":
        if st.session_state.num_new_words > 0:
            st.session_state.page = "recall_words"
        else:
            with modal.container():
                st.write("请输入正确的单词数量！")



    #显示侧边栏
    with st.sidebar:
        st.header("设置")
        level = st.selectbox(
            "选择你的词汇水平",
            ["CET6"],
            help="目前仅支持CET6水平检测"
        )

        num_words = int(st.number_input("输入要复习的生词数量"))
        st.session_state.num_new_words = num_words


    if st.session_state.page == "PDF":
        #调用main方法显示主页面
        main()
    elif st.session_state.page == "recall_words":
        recall_new_words()
