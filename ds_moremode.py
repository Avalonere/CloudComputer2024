import requests
from openai import OpenAI

class DeepSeekAPI:
    def __init__(self, api_key, base_url="https://api.deepseek.com"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def call_api(self, prompt, mode="dialogue", user_language="zh", max_tokens=2000, stream=False, config=None):
        """
        调用 DeepSeek API 生成内容。
        :param prompt: 输入的文本内容
        :param user_language: 用户语言
        :param max_tokens: 最大 token 数
        :param stream: 是否流式输出
        :return: 生成的文本内容
        """
        if config:
            # 从 config 中提取配置项并使用它们
            mode = config.get("mode", mode)
            user_language = config.get("user_language", user_language)
        # 模式处理
        if mode == "dialogue":
            prompt_text = (
                f"使用用户语言直接交流。\n"
                f"{prompt}"
            )
        elif mode == "generating":
            # 教学模式下构建 prompt
            prompt_text = (
                f"请直接把传入内容翻译成{user_language}。\n"
                f"{prompt}"
            )
        elif mode == "translate":
            # 翻译模式下构建 prompt
            prompt_text = (
                f"请将以下内容翻译为中文：\n"
                f"{prompt}"
            )
        elif mode == "synthesize":
            # 文件翻译模式下构建 prompt"
            prompt_text = (
                f"请将以下内容翻译为{user_language}：\n"
                f"{prompt}"
            )
        else:
            return "Invalid mode. Please select 'dialogue', 'teaching', 'translate', or 'file_translate'."

        # 检查是否有实际问题被提出
        if not prompt.strip():
            return "您还未提供具体的问题，请输入问题后重试。"

        # 调用 API
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Please respond in the language the user uses."},
                    {"role": "user", "content": prompt_text},
                ],
                stream=stream,
                max_tokens=max_tokens
            )
            if stream:
                output = ""
                for chunk in response:
                    content = chunk.choices[0].delta.get("content", "")
                    print(content, end="", flush=True)
                    output += content
                return output.strip()
            else:
                return response.choices[0].message.content.strip()

        except Exception as e:
            return f"API 调用失败：{e}"


# # 示例使用
# if __name__ == "__main__":
#     # 用户选择模式
#     print("模式选项：")
#     print("1. 对话模式 (dialogue): 根据用户提问的语言直接回答。")
#     print("2. 教学模式 (teaching): 提供分步骤回答，包括领域说明和翻译。")
#     print("3. 翻译模式 (translate): 将用户输入翻译为中文。")
#     print("4. 文件翻译模式 (file_translate): 翻译用户上传的文件内容。")

#     user_mode_input = input("请选择模式（1, 2, 3 或 4）：").strip()
#     mode_mapping = {"1": "dialogue", "2": "teaching", "3": "translate", "4": "file_translate"}
#     user_mode = mode_mapping.get(user_mode_input)

#     while not user_mode:
#         print("模式无效，请输入 1, 2, 3 或 4。")
#         user_mode_input = input("请选择模式（1, 2, 3 或 4）：").strip()
#         user_mode = mode_mapping.get(user_mode_input)

#     # 用户输入问题或文件内容
#     if user_mode == "file_translate":
#         file_path = input("请输入文件路径：").strip()
#         try:
#             with open(file_path, "r", encoding="utf-8") as file:
#                 user_prompt = file.read()
#         except Exception as e:
#             print(f"文件读取失败：{e}")
#             exit()
#         target_language = input("请输入目标语言（如：少数民族语言）：").strip()
#     else:
#         user_prompt = input("请输入您的问题：").strip()
#         while not user_prompt:
#             print("问题不能为空，请重新输入。")
#             user_prompt = input("请输入您的问题：").strip()
#         target_language = None

#     # 用户语言（动态获取用户提问的语言）
#     user_language = "zh"  # 可以动态扩展为根据输入检测语言

#     # 调用函数
#     api_key = "sk-999b033b56194cf7a13453575412d299"  # 替换为你的 API 密钥
#     deepseek = DeepSeekAPI(api_key)
#     result = deepseek.call_api(
#         prompt=user_prompt,
#         mode=user_mode,
#         target_language=target_language,
#         max_tokens=4000  # 支持长文本
#     )

#     # 输出结果
#     print(result)