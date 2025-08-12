#!/usr/bin/env python3
"""
测试图片处理功能的客户端
"""
import requests
import json
import base64

# base_url = "http://localhost:8080/v1/chat/completions"
base_url = "https://llm-proxy-605029883265.us-central1.run.app/v1/chat/completions"
# 使用一个公开的测试图片URL
image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/1280px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
   

def image_to_base64(image_path):
    """
    将图片文件转换为base64编码字符串
    
    Args:
        image_path (str): 图片文件路径
        
    Returns:
        str: base64编码字符串
    """
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_string = base64.b64encode(image_data).decode('utf-8')
            return base64_string
    except FileNotFoundError:
        print(f"错误：找不到文件 {image_path}")
        return None
    except Exception as e:
        print(f"错误：转换图片时出现问题 - {str(e)}")
        return None

tiny_png_base64 = image_to_base64("20250803_1038_生日派对祝贺_remix_01k1pwhdhdfqnvgz1zfs9cdmfw.png")
print(tiny_png_base64)
def test_text_only():
    """测试纯文本消息"""
    print("🧪 测试纯文本消息...")
    
    data = {
        "model": "gemini-2.5-pro",
        "messages": [
            {
                "role": "user", 
                "content": "你好，请说一句话。"
            }
        ],
        "stream": False
    }
    
    response = requests.post(
        base_url,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 纯文本测试成功: {result['choices'][0]['message']['content'][:50]}...")
    else:
        print(f"❌ 纯文本测试失败: {response.status_code} - {response.text}")

def test_image_base64():
    """测试Base64编码的图片"""
    print("\n🧪 测试Base64图片...")
    
    # 创建一个简单的1x1像素的PNG图片（Base64编码）
    # 这是一个透明的1x1像素PNG图片

    data = {
        "model": "gemini-2.5-pro",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请描述这张图片的内容。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{tiny_png_base64}"
                        }
                    }
                ]
            }
        ],
        "stream": False
    }
    
    response = requests.post(
        base_url,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Base64图片测试成功: {result['choices'][0]['message']['content'][:100]}...")
    else:
        print(f"❌ Base64图片测试失败: {response.status_code} - {response.text}")

def test_image_url():
    """测试URL形式的图片"""
    print("\n🧪 测试URL图片...")
    
 
    data = {
        "model": "gemini-2.5-pro", 
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请描述这张图片。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "stream": False
    }
    
    response = requests.post(
        base_url,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ URL图片测试成功: {result['choices'][0]['message']['content'][:100]}...")
    else:
        print(f"❌ URL图片测试失败: {response.status_code} - {response.text}")

def test_mixed_content():
    """测试混合内容（文本 + 多张图片）"""
    print("\n🧪 测试混合内容...")
    
    data = {
        "model": "gemini-2.5-pro",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "我有两张图片要展示给你："
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{tiny_png_base64}"
                        }
                    },
                    {
                        "type": "text", 
                        "text": "第一张图片是上面的。现在是第二张："
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "请分别描述这两张图片。"
                    }
                ]
            }
        ],
        "stream": False
    }
    
    response = requests.post(
        base_url,
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 混合内容测试成功: {result['choices'][0]['message']['content'][:100]}...")
    else:
        print(f"❌ 混合内容测试失败: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("🚀 开始测试图片处理功能...\n")
    
    try:
        test_text_only()
        test_image_base64() 
        test_image_url()
        test_mixed_content()
        
        print("\n✨ 所有测试完成！")
    except Exception as e:
        print(f"\n💥 测试过程中出错: {str(e)}") 