"""
API调用示例
提供一个利用API进行多轮对话的简单示例    
"""
import os
from openai import OpenAI
from openai import AsyncOpenAI
from llm_toolkit import ModelConfigManager


# 如果采用openai等外网官方网站作为base_url，需要设置下代理的映射端口
# os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7897'
# os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7897'
# os.environ['ALL_PROXY'] = 'http://127.0.0.1:7897'

# 设置在通过该网址访问时不使用任何代理，否则在开启vpn通过该网站调用api会出错
os.environ['NO_PROXY'] = 'api.agicto.cn'

def initialize_client(api_key, base_url):
    if not api_key:
        raise ValueError("api_key为空, 请检查环境变量是否设置!")
    
    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )

def chat_single(config_manager: ModelConfigManager, provider: str, model: str):
    model_config = config_manager.get_model_config(provider, model)
    client = initialize_client(api_key=model_config['api_key'], base_url=model_config['base_url'])
    
    system_prompt = "You are a helpful assistant, please add '>_<' after answering each question."
    user_message = "Hello!"
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    print(f"使用模型: {model_config['provider']} - {model_config['model']}")
    print(f"模型描述: {model_config['description']}")

    response = client.chat.completions.create(
        model = model_config['model'],
        messages = conversation,
        stream = False
    )
    
    print(f"LLM🤖: {response.choices[0].message.content}")
    # 对于思考模型，可以通过reasoning_content访问思维链
    # print(f"LLM🤖: {response.choices[0].message.reasoning_content}")

def chat_multi(config_manager: ModelConfigManager, provider: str, model: str):
    model_config = config_manager.get_model_config(provider, model)
    client = initialize_client(api_key=model_config['api_key'], base_url=model_config['base_url'])
    system_prompt = "You are a helpful assistant, please add '>_<' after answering each question."
    conversation = [
        {"role": "system", "content": system_prompt}
    ] 
    
    print(f"使用模型: {model_config['provider']} - {model_config['model']}")
    print(f"模型描述: {model_config['description']}")
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
        response = client.chat.completions.create(
            model = model_config['model'],
            messages = conversation,
            stream = False
        )
        
        ai_response = response.choices[0].message.content
        conversation.append({"role": "assistant", "content": ai_response})
        print(f"LLM🤖: {ai_response}")

if __name__ == "__main__":
    config_manager = ModelConfigManager()
    provider = 'qwen'           # 提供商
    model = 'qwen3-vl-plus'     # 模型名称

    # chat_single(config_manager, provider, model)       # 单轮对话测试
    chat_multi(config_manager, provider, model)         # 多轮对话测试
    