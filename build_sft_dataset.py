"""
将图像转换为调用LLM API的格式

输入包含图像的文件夹和提示词（建议从pe.json文件中提取），自动构造json格式数据.

author:zhaoshe
"""
import os
from pathlib import Path
from typing import Literal
from collections import defaultdict
import json
from tqdm import tqdm
import argparse

def load_prompt(pe_json_path: str='./dataset/pe.json', idx: int=0) -> str:
    """根据输入的idx，加载相应的prompt

    Args:
        pe_json_path(str): 存储prompt的json文件路径
        idx (int): prompt的编号

    Returns:
        str: 对应的prompt
    """
    with open(pe_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prompt = f"prompt{idx}"
    return data[prompt]['prompt_text']

def build_item_single_image(
    image_dir: str,
    prompt: str,
    sft_dataset_path: str
) -> None:
    """为图像和prompt生成相应的json数据,单图模式

    Args:
        image_dir (str): 图像文件夹
        prompt (str): 对应的提示词
        sft_dataset_path(str): 保存的json文件路径
    """
    image_suffix = ('.jpg', '.jpeg', '.png', '.bmp')

    # 读取已存在的id
    existing_ids = set()
    if os.path.exists(sft_dataset_path):
        with open(sft_dataset_path, 'r', encoding='utf-8') as f_in:
            for line in f_in:
                try:
                    data = json.loads(line.strip())
                    existing_ids.add(data['id'])
                except (json.JSONDecodeError, KeyError):
                    continue
    
    try:
        with open(sft_dataset_path, 'a', encoding='utf-8') as f_out:
            for image_name in tqdm(os.listdir(image_dir), desc="Processing images"):
                try:
                    if not image_name.lower().endswith(image_suffix):
                        continue
                    
                    # 检查id是否已存在
                    if image_name in existing_ids:
                        print(f"跳过已存在的图像: {image_name}")
                        continue
                    
                    image_path = Path(image_dir) / image_name
                    absolute_image_path = image_path.absolute().as_posix()      # 转化为绝对路径，再as_posix()强制转化为/连接
                    new_entry = {
                        'id': image_path.stem,
                        'image': [absolute_image_path],
                        'conversation': [
                            {'from': 'human', 'value': prompt},
                            {'from': 'assistant', 'value': ''}
                        ]
                    }

                    f_out.write(json.dumps(new_entry, ensure_ascii=False) + '\n')
                except Exception as e:
                    print(f"处理图像{image_name}时发生错误 {e}, 已跳过")

    except Exception as e:
        print(f"写入 JSONL 时出错: {e}")

def build_item_multi_image(
    image_dir: str,
    prompt: str,
    sft_dataset_path: str,
    multi_mode: Literal['prefix', 'suffix'] = 'prefix'
) -> None:
    """根据图像和prompt生成相应的jsonl数据,多图模式,需保证同一组输入的前缀或者后缀相同。

    Args:
        image_dir (str): 图像文件夹
        prompt (str): 对应的提示词
        sft_dataset_path (str): 保存的json文件路径
        multi_mode (Literal['prefix', 'suffix'], optional): 若同一组图像前缀相同则设置为prefix, 后缀相同设置为suffix.
    """

    groups = defaultdict(list)
    image_suffix = ('.jpg', '.jpeg', '.png', '.bmp')
    
    # 读取已存在的id
    existing_ids = set()
    if os.path.exists(sft_dataset_path):
        with open(sft_dataset_path, 'r', encoding='utf-8') as f_in:
            for line in f_in:
                try:
                    data = json.loads(line.strip())
                    existing_ids.add(data['id'])
                except (json.JSONDecodeError, KeyError):
                    continue
        
    try:
        with open(sft_dataset_path, 'a', encoding='utf-8') as f_out:
            # 对图像根据前缀/后缀进行分组，后续为每组图像生成唯一的json对象
            for image_name in tqdm(os.listdir(image_dir), desc = "Processing images:"):
                try:
                    if not image_name.lower().endswith(image_suffix):
                        continue
                
                    image_path = Path(image_dir) / image_name
                    part = image_path.stem.split('_')
                    absolute_image_path = image_path.absolute().as_posix()
                    
                    if multi_mode == 'prefix':
                        prefix = part[0]
                        groups[prefix].append(absolute_image_path)
                        
                    elif multi_mode == 'suffix':
                        suffix = part[-1]
                        groups[suffix].append(absolute_image_path)
                    else:
                        raise ValueError(f"不支持的前后缀格式！")
                    
                except Exception as e:
                    print(f"处理图像{image_name}时发生错误 {e}, 已跳过")
            
            for pre_suffix, absolute_image_path in groups.items():
                try:
                    # 检查id是否已经存在
                    if pre_suffix in existing_ids:
                        print(f"跳过已存在的图像组: {pre_suffix}")
                        continue    
                                    
                    new_entry = {
                        'id': pre_suffix,
                        'image': absolute_image_path,
                        'conversation': [
                            {'from': 'human', 'value': prompt},
                            {'from': 'assistant', 'value': ''}
                        ]
                    }
                    
                    f_out.write(json.dumps(new_entry, ensure_ascii=False) + '\n')
                    
                except Exception as e:
                    print(f"保存前/后缀为 {pre_suffix} 的图像组时发生错误 {e}, 已跳过该组图像")  
                
    except Exception as e:
        print(f"写入 JSONL 时出错: {e}")


def main():
    parser = argparse.ArgumentParser(description='构建SFT数据集')
    parser.add_argument('--image_dir', required=True, type=str, default='./example/images', help='输入图像文件夹路径')
    parser.add_argument('--output_file', type=str, default='./example/sft_dataset.jsonl', help='输出JSONL文件路径')
    parser.add_argument('--pe_json_path', type=str, default='./example/pe.json', help='prompt JSON文件路径')
    parser.add_argument('--prompt_idx', type=int, default=0, help='使用的prompt索引')
    parser.add_argument('--mode', type=str, choices=['single', 'multi'], default='single', help='模式选择: single(单图) 或 multi(多图)')
    parser.add_argument('--multi_mode', type=str, choices=['prefix', 'suffix'], default='prefix', help='多图模式下的分组方式: prefix(前缀) 或 suffix(后缀)')
    
    args = parser.parse_args()
    
    # 加载提示词
    prompt = load_prompt(pe_json_path=args.pe_json_path, idx=args.prompt_idx)
    
    # 根据模式调用相应的函数
    if args.mode == 'single':
        build_item_single_image(args.image_dir, prompt, args.output_file)
    elif args.mode == 'multi':
        build_item_multi_image(args.image_dir, prompt, args.output_file, mode=args.multi_mode)
    else:
        raise ValueError(f"不支持的模式: {args.mode}")

if __name__ == "__main__":
    # 通过命令行调用(不建议)
    # main()
    
    image_dir = './example/images'                                      # 输入图像文件夹
    prompt = load_prompt(pe_json_path='./example/pe.json', idx=2)       # 从pe.json中加载相应的prompt
    output_file = './example/sft_dataset_single.jsonl'          # 输出文件的路径 
    
    # 输入单张图像，生成sft格式数据
    build_item_single_image(image_dir, prompt, output_file)
   
    # 输入多张图像，生成sft格式数据 
    # build_item_multi_image(image_dir, prompt, output_file, multi_mode='prefix')
