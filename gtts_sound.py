from gtts import gTTS
import os

def generate_speech(text, lang='en', output_file='output_audio.mp3'):
    try:
        # 使用 gTTS 生成语音
        tts = gTTS(text=text, lang=lang, slow=False)  # slow=False 表示快速发音
        tts.save(output_file)

        print(f"语音已成功生成并保存为: {output_file}")
        return output_file

    except Exception as e:
        print(f"语音生成失败: {e}")
        return None

