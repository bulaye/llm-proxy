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
import tempfile

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

def process_message_content(content):
    """处理消息内容，支持文本和图片的混合内容"""
    parts = []
    
    if isinstance(content, str):
        # 简单文本消息
        parts.append(Part.from_text(content))
    elif isinstance(content, list):
        # 结构化内容，可能包含文本和图片
        for item in content:
            if item.get("type") == "text":
                parts.append(Part.from_text(item.get("text", "")))
            elif item.get("type") == "image_url":
                image_url = item.get("image_url", {}).get("url", "")
                if image_url:
                    try:
                        if image_url.lower().startswith("gs://"):
                            mime_type, _ = mimetypes.guess_type(image_url)
                            parts.append(Part.from_uri(uri=image_url, mime_type=mime_type))
                        elif image_url.lower().startswith(("http://", "https://")):
                            # 远程URL
                            mime_type, _ = mimetypes.guess_type(image_url)
                            parts.append(Part.from_uri(uri=image_url, mime_type=mime_type))
                        elif image_url.strip().startswith("data:image"):
                            try:
                                # 解析 Data URI: data:[<mime_type>];base64,[<data>]
                                header, encoded_data = image_url.split(",", 1)
                                mime_type = header.split(";")[0].split(":")[1]
                                # 将 base64 字符串解码为字节
                                decoded_data = base64.b64decode(encoded_data)
                                parts.append(Part.from_data(data=decoded_data, mime_type=mime_type))
                            except (ValueError, IndexError) as e:
                                raise ValueError(f"无效的 Base64 Data URI 格式: {e}")
                        # 4. 检查是否为本地文件
                        elif os.path.isfile(image_url):
                            mime_type, _ = mimetypes.guess_type(image_url)
                            if not mime_type:
                                raise ValueError(f"无法确定文件 '{image_url}' 的 MIME 类型。")
                                
                            with open(image_url, "rb") as f:
                                image_data = f.read()
                            return Part.from_data(data=image_data, mime_type=mime_type)

                        # 5. 如果以上都不是，则是无效输入
                        else:
                            raise FileNotFoundError(
                                f"输入 '{image_url}' 不是一个有效的 GCS URI、HTTPS URL、Base64 Data URI 或存在的本地文件路径。"
                            )
                    except Exception as e:
                        print(f"错误: 处理图片时出错 - {str(e)}")
                        continue
    else:
        # 其他格式，转为文本
        parts.append(Part.from_text(str(content)))
    
    return parts


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
                contents.append(Content(role="model", parts=process_message_content(content)))
            elif role == "user":
                contents.append(Content(role="user", parts=process_message_content(content)))
        
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