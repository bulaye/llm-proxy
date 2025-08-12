from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Content, Part
import json
import os
from dotenv import load_dotenv
import uuid
import time
import base64
import mimetypes
import requests

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化Vertex AI
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "bulayezhou")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
vertexai.init(project=project_id, location=location)


import base64
import requests
import re
from vertexai.generative_models import Content, Part, Image

def extract_base64_from_data_uri(data_uri):
    """从数据 URI 中提取 Base64 编码的数据"""
    # 匹配格式：data:[<mediatype>][;base64],<data>
    match = re.search(r"data:image\/\w+;base64,(.+)", data_uri)
    if match:
        return match.group(1)
    # 如果格式不标准，尝试直接获取逗号后的内容
    if "," in data_uri:
        return data_uri.split(",", 1)[1]
    return data_uri  # 可能已经是纯 Base64

def download_image(url):
    """下载远程图片"""
    response = requests.get(url)
    response.raise_for_status()  # 确保请求成功
    return response.content


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "gemini-proxy-vertex",
        "model": "gemini-2.5-pro" 
    })

@app.route('/v1/chat/completions', methods=['POST'])
@app.route('/chat/completions', methods=['POST'])
def chat_completions():
    """聊天接口 - 协议转换代理"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        stream = data.get('stream', False)
        model_name = data.get('model', "gemini-2.5-pro")
        
        # OpenAI到Vertex AI的基本转换
        system_instruction = None
        contents = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
            elif role == "assistant":
                # assistant -> model
                contents.append(Content(role="model", parts=[Part.from_text(content)]))
            elif role == "user":
                # 处理用户消息，支持文本和图片
                parts = []
                
                if isinstance(content, str):
                    # 纯文本消息
                    parts.append(Part.from_text(content))
                elif isinstance(content, list):
                    # 多模态消息（文本 + 图片）
                    for item in content:
                        if item["type"] == "text":
                        # 处理文本部分
                        parts.append(Part.from_text(item["text"]))
                        
                    elif item["type"] == "image_url":
                        url_or_data = item["image_url"]["url"]
                        
                        # 检查是否是 Base64 数据 URI（格式如：data:image/png;base64,iVBORw0...）
                        if url_or_data.startswith("data:image/"):
                            # 从数据 URI 中提取 Base64 部分
                            base64_data = extract_base64_from_data_uri(url_or_data)
                            parts.append(Part.from_image(Image.from_base64(base64_data)))
                            
                        elif url_or_data.startswith(("http://", "https://")):
                            # 处理 HTTP/HTTPS URL
                            image_data = download_image(url_or_data)
                            base64_image = base64.b64encode(image_data).decode("utf-8")
                            parts.append(Part.from_image(Image.from_base64(base64_image)))
                            
                        else:
                            # 其他情况（可能是本地路径或 GCS URI）
                            # 注意：Vertex AI 原生支持 GCS URI（gs://...）
                            parts.append(Part.from_image(Image.load_from_file(url_or_data)))
                
                if parts:
                    contents.append(Content(role="user", parts=parts))
        
        # 创建模型
        model_kwargs = {}
        if system_instruction:
            model_kwargs['system_instruction'] = system_instruction
        model = GenerativeModel(model_name, **model_kwargs)

        # 基本生成配置
        config_params = {}
        if 'temperature' in data:
            config_params['temperature'] = data['temperature']
        if 'top_p' in data:
            config_params['top_p'] = data['top_p']
        if 'max_output_tokens' in data:
            config_params['max_output_tokens'] = data['max_output_tokens']
        
        generation_config = GenerationConfig(**config_params) if config_params else None
        
        if stream:
            def generate_stream():
                response_id = f"chatcmpl-{uuid.uuid4()}"
                created_time = int(time.time())
                
                generate_params = {'contents': contents, 'stream': True}
                if generation_config:
                    generate_params['generation_config'] = generation_config
                
                response_stream = model.generate_content(**generate_params)
                
                # 首个chunk包含角色信息
                first_chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(first_chunk)}\n\n"

                # 流式内容
                for chunk in response_stream:
                    if chunk.text:
                        chunk_data = {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model_name,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk.text},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                # 结束标记
                final_chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            
            return Response(generate_stream(), mimetype='text/event-stream')
        else:
            generate_params = {'contents': contents}
            if generation_config:
                generate_params['generation_config'] = generation_config
            
            response = model.generate_content(**generate_params)

            response_data = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0
                }
            }
            return jsonify(response_data)
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Gemini代理服务启动: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 