from fastapi import FastAPI, UploadFile, File, Form, Response  # 导入 Response
from pydantic import BaseModel
from gtts_sound import generate_speech
import uvicorn
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from tencentdb import TxtFile,UsageStats
from ds_moremode import DeepSeekAPI

app = FastAPI()

# 数据库连接
DATABASE_URL = "mysql+pymysql://root:data1234@sh-cdb-nncpvxj4.sql.tencentcdb.com:27709/my_db?charset=utf8mb4"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表
class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

class GenerateRequest(BaseModel):
    content: str
    target_lang: str

class SynthesizeRequest(BaseModel):
    text: str
    lang: str

class ChatRequest(BaseModel):
    message: str
    lang: str

# 创建类实例
deepseek_api = DeepSeekAPI(api_key="sk-999b033b56194cf7a13453575412d299")

# 接口：根目录
@app.get("/")
async def read_root():
    return {"message": "Welcome to the DeepSeek API!"}

# 接口：对话
@app.post("/chat")
async def chat(request: ChatRequest):
    print(f"Received message: {request.message}, language: {request.lang}")

    response = deepseek_api.call_api(request.message, config={"mode": "dialogue", "user_language": request.lang})
    session = SessionLocal()
    stat = session.query(UsageStats).filter_by(feature="chat").first()
    if stat:
        stat.count += 1
    else:
        stat = UsageStats(feature="chat", count=1)
        session.add(stat)
    session.commit()
    session.close()
    return {"response": response}

# 接口：翻译
@app.post("/translate")
async def translate(request: TranslationRequest):
    translation_result = deepseek_api.call_api(request.text, config={"mode": "translate", "user_language": request.source_lang})
    session = SessionLocal()
    stat = session.query(UsageStats).filter_by(feature="translate").first()
    if stat:
        stat.count += 1
    else:
        stat = UsageStats(feature="translate", count=1)
        session.add(stat)
    session.commit()
    session.close()
    return {"translation": translation_result}

# 接口：生成
@app.post("/generate")
async def generate(request: GenerateRequest):
    generated_text = deepseek_api.call_api(request.content, config={"mode": "generating", "user_language": request.target_lang})
    session = SessionLocal()
    stat = session.query(UsageStats).filter_by(feature="generate").first()
    if stat:
        stat.count += 1
    else:
        stat = UsageStats(feature="generate", count=1)
        session.add(stat)
    session.commit()
    session.close()
    return {"generated_text": generated_text}

# 接口：上传文本文件
@app.post("/upload_txt")
async def upload_txt(file: UploadFile = File(...), file_name: str = Form(...)):
    content = await file.read()
    content_str = content.decode("utf-8")
    session = SessionLocal()
    new_file = TxtFile(file_name=file_name, file_content=content_str)
    session.add(new_file)
    session.commit()
    session.close()
    return {"message": "File uploaded successfully"}

# 接口：合成语音
@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    text = request.text
    lang = request.lang

    translated_text = deepseek_api.call_api(prompt=text, user_language=lang, mode="synthesize")
    print(f"翻译后的文本：{translated_text}")

    # tts = generate_speech(text=translated_text, lang=lang)
    # if tts is None:
    #     return {"error": "语音生成失败，不支持的语言或生成错误"}
    # tts.save("output_audio.mp3")
    # with open("output_audio.mp3", "rb") as f:
    #     audio_content = f.read()
    
    # 生成语音文件
    audio_file_path = generate_speech(text=translated_text, lang=lang)
    if audio_file_path is None:
        return {"error": "语音生成失败，不支持的语言或生成错误"}

    # 读取生成的音频文件内容
    with open(audio_file_path, "rb") as f:
        audio_content = f.read()
        
    session = SessionLocal()
    stat = session.query(UsageStats).filter_by(feature="synthesize").first()
    if stat:
        stat.count += 1
    else:
        stat = UsageStats(feature="synthesize", count=1)
        session.add(stat)
    session.commit()
    session.close()
    # 返回音频文件内容
    return Response(content=audio_content, media_type="audio/mp3")

# 接口：获取用量统计
@app.get("/usage_stats")
async def get_usage_stats():
    session = SessionLocal()
    stats = session.query(UsageStats).all()
    session.close()
    return [{"feature": stat.feature, "count": stat.count} for stat in stats]

# 启动服务
if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)