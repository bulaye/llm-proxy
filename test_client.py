#!/usr/bin/env python3
"""
Gemini Vertex AI代理API测试客户端
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8080"

def test_health():
    """测试健康检查接口"""
    print("🔍 测试健康检查接口...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_chat_non_stream():
    """测试非流式聊天接口"""
    print("\n💬 测试非流式聊天接口 (OpenAI兼容模式)...")
    data = {
        "model": "gemini-2.5-pro",
        "messages": [
            {
                "role": "system",
                "content": "你是一个乐于助人的助手。"
            },
            {
                "role": "user",
                "content": "你好，请用一句话介绍一下Google Gemini"
            }
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", json=data)
        response.raise_for_status()
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        content = result['choices'][0]['message']['content']
        print(f"助手回答: {content}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 非流式聊天测试失败: {e}")
        if e.response:
            print(f"   错误详情: {e.response.text}")
        return False

def test_chat_stream():
    """测试流式聊天接口"""
    print("\n🌊 测试流式聊天接口 (OpenAI兼容模式)...")
    data = {
        "model": "gemini-2.5-pro",
        "messages": [
             {
                "role": "user",
                "content": "请写一个简单的Python函数来计算斐波那契数列"
            }
        ],
        "stream": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", json=data, stream=True)
        response.raise_for_status()
        print(f"状态码: {response.status_code}")
        
        print("流式响应:")
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str == 'data: [DONE]':
                    print("\n✅ 流式响应完成")
                    break
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    try:
                        chunk_data = json.loads(data_str)
                        content = chunk_data['choices'][0]['delta'].get('content', '')
                        print(content, end='', flush=True)
                        full_response += content
                    except (json.JSONDecodeError, KeyError):
                        # 忽略空的或格式不正确的块
                        continue
        if not full_response:
             print("\n⚠️ 流式响应为空")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ 流式聊天测试失败: {e}")
        if e.response:
            print(f"   错误详情: {e.response.text}")
        return False

def main():
    """运行所有测试"""
    print("🚀 开始测试Gemini Vertex AI代理API...")
    print(f"📍 目标地址: {BASE_URL}")
    print("=" * 50)
    
    # 确保服务已启动
    if not test_health():
        print("\n❌ 服务健康检查失败，无法继续测试。请确保app_vertex.py正在运行。")
        return

    tests = [
        ("非流式聊天", test_chat_non_stream),
        ("流式聊天", test_chat_stream),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
            time.sleep(1)
        except Exception as e:
            print(f"❌ {test_name}测试出现意外异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    passed_tests = []
    failed_tests = []
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
        if success:
            passed_tests.append(test_name)
        else:
            failed_tests.append(test_name)

    passed = len(passed_tests)
    total = len(results)
    print(f"\n🎯 总体结果: {passed}/{total} 测试通过")
    if failed_tests:
        print(f"   失败的测试: {', '.join(failed_tests)}")


if __name__ == "__main__":
    main() 