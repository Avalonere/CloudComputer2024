FROM langchain/langchain

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade -r requirements.txt

# 复制需要的文件到容器中
COPY user.py .          
COPY utils.py . 
COPY chains.py .
COPY DBtest.py .
COPY CET_4_6_edited.txt /app

EXPOSE 8506

HEALTHCHECK CMD curl --fail http://localhost:8506/_stcore/health

ENTRYPOINT ["streamlit", "run", "./user.py", "--server.port=8506", "--server.address=0.0.0.0"]
