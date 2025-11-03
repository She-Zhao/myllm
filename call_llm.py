"""
API调用示例
提供一个利用API进行多轮对话的简单示例    
"""
import os
from openai import OpenAI

def initialize_client(api_key, base_url):
    if not api_key:
        raise ValueError("api_key为空, 请检查环境变量是否设置!")
    
    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )

def chat_with_llm(client, conversation_history, model):
    try:
        response = client.chat.completions.create(
            model = model,
            messages = conversation_history,
            stream = False
        )
        return response.choices[0].message.content
    
    except Exception as e:
        return f"API调用失败: {e}"

def chat_single(api_key, base_url, model):
    client = initialize_client(api_key, base_url)
    system_prompt = "You are a helpful assistant, please add '>_<' after answering each question."
    user_message = "Hello!"
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    response = client.chat.completions.create(
        model = model,
        messages = conversation,
        stream = False
    )
    print(f"LLM🤖: {response.choices[0].message.content}")

def chat_multi(api_key, base_url, model):
    client = initialize_client(api_key=api_key, base_url=base_url)
    system_prompt = "You are a helpful assistant, please add '>_<' after answering each question."
    conversation = [
        {"role": "system", "content": system_prompt}
    ] 
    
    print("开始多轮对话，输入 'q' 退出\n")
    while True:
        user_input = input('human👤:').strip()
        if user_input == 'q':
            print('对话结束！')
            break
        
        if not user_input:
            print('用户输入不能为空!')
            continue
        
        conversation.append({"role": "user", "content": user_input})
        response = chat_with_llm(client, conversation, model)
        
        conversation.append({"role": "assistant", "content": response})
        print(f"LLM🤖: {response}")

if __name__ == "__main__":
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = "https://api.deepseek.com"
    model = "deepseek-chat"
    
    chat_single(api_key, base_url, model)       # 单轮对话测试
    # chat_multi(api_key, base_url, model)      # 多轮对话测试
    