from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting, HarmCategory, Content, Part
import json
import os
from dotenv import load_dotenv
import uuid
import time
import base64
import refrom flask import Flask, request, jsonify, Response
from flask_cors import CORS
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Content, Part
import json
import os
from dotenv import load_dotenv
import uuid
import time

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化Vertex AI
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "bulayezhou")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
vertexai.init(project=project_id, location=location)

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
                # user保持不变，简单转换content
                contents.append(Content(role="user", parts=[Part.from_text(str(content))]))
        
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
import urllib.request

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app, origins="*", methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"])  # 更详细的CORS配置

# 初始化Vertex AI
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "bulayezhou")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1") # 使用支持的区域
vertexai.init(project=project_id, location=location)

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
    """聊天接口 - 支持流式和非流式响应, 兼容OpenAI协议"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        
        messages = data.get('messages', [])
        stream = data.get('stream', False)
        
        if not messages:
            return jsonify({"error": "消息内容不能为空"}), 400
        
        # 处理 messages, 提取 system prompt 和转换角色
        system_instruction = None
        contents = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if not content:
                continue

            if role == "system":
                system_instruction = content
                continue
            
            # Vertex AI 的角色是 'user' 和 'model'
            if role == "assistant":
                role = "model"
            
            if not isinstance(content, list):
                # 兼容纯文本 content
                contents.append(Content(role=role, parts=[Part.from_text(str(content))]))
                continue
            
            # 处理多模态 content
            # The 'user' role is the only one that can contain multi-part content.
            if role != "user":
                app.logger.warning(f"Only user role can have multimodal content, but got {role}. Skipping message.")
                continue

            parts = []
            for part_data in content:
                part_type = part_data.get("type")
                if part_type == "text":
                    text = part_data.get("text")
                    if text:
                        parts.append(Part.from_text(text))
                elif part_type == "image_url":
                    image_url_data = part_data.get("image_url")
                    if image_url_data:
                        url = image_url_data.get("url")
                        if not url:
                            continue
                        
                        if url.startswith("data:"):
                            try:
                                # 解析 data URI, e.g. "data:image/png;base64,iVBORw..."
                                match = re.match(r"data:(?P<mime_type>[\w/\-\.]+);base64,(?P<data>.*)", url)
                                if match:
                                    mime_type = match.group('mime_type')
                                    base64_data = match.group('data')
                                    image_data = base64.b64decode(base64_data)
                                    parts.append(Part.from_data(mime_type=mime_type, data=image_data))
                                else:
                                    app.logger.warning(f"Could not parse data URI for image.")
                            except Exception as e:
                                app.logger.error(f"Error decoding base64 image: {e}")
                        elif url.startswith("http"):
                            try:
                                with urllib.request.urlopen(url) as response:
                                    image_data = response.read()
                                    mime_type = response.info().get_content_type()
                                    parts.append(Part.from_data(data=image_data, mime_type=mime_type))
                            except Exception as e:
                                app.logger.error(f"Error fetching image from URL {url}: {e}")

            if parts:
                contents.append(Content(role=role, parts=parts))
        
        # 获取模型
        model_name = data.get('model', "gemini-2.5-pro")
        if not contents:
             return jsonify({"error": "有效消息内容不能为空"}), 400
        
        # 检查是否所有消息都是 'user' 或 'model' 角色
        for content_item in contents:
            if content_item.role not in ['user', 'model']:
                 return jsonify({"error": f"无效的角色: {content_item.role}. 只接受 'user' 和 'model'."}), 400
        
        model_kwargs = {}
        if system_instruction:
            model_kwargs['system_instruction'] = system_instruction
        
        model = GenerativeModel(model_name, **model_kwargs)

        # 配置生成参数
        generation_config = GenerationConfig(
            temperature=data.get('temperature', 1.0),
            top_p=data.get('top_p', 0.95),
            max_output_tokens=data.get('max_output_tokens', 8192),
        )
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: SafetySetting.HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: SafetySetting.HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: SafetySetting.HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: SafetySetting.HarmBlockThreshold.BLOCK_NONE,
        }
        
        if stream:
            def generate_stream():
                response_id = f"chatcmpl-{uuid.uuid4()}"
                created_time = int(time.time())
                
                try:
                    response_stream = model.generate_content(
                        contents,
                        generation_config=generation_config,
                        safety_settings=safety_settings,
                        stream=True
                    )
                    
                    # 发送第一个包含角色的块
                    first_chunk_data = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model_name,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"role": "assistant", "content": ""},
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(first_chunk_data)}\n\n"

                    for chunk in response_stream:
                        delta = {}
                        if chunk.text:
                            delta['content'] = chunk.text
                        
                        finish_reason = None
                        if chunk.candidates and chunk.candidates[0].finish_reason:
                            fr_name = chunk.candidates[0].finish_reason.name
                            if fr_name == 'STOP':
                                finish_reason = 'stop'
                            elif fr_name == 'MAX_TOKENS':
                                finish_reason = 'length'
                            elif fr_name == 'SAFETY':
                                finish_reason = 'content_filter'
                            else:
                                finish_reason = 'stop' # 默认

                        chunk_data = {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": created_time,
                            "model": model_name,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": delta,
                                    "finish_reason": finish_reason
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    # 发送最终的结束块，确保客户端知道流已结束
                    final_chunk_data = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model_name,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }
                        ]
                    }
                    yield f"data: {json.dumps(final_chunk_data)}\n\n"
                    
                    # 发送标准的结束标记
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    error_data = {"error": str(e), "type": "error"}
                    yield f"data: {json.dumps(error_data)}\n\n"
                    yield "data: [DONE]\n\n"
            
            # 设置正确的响应头，确保客户端能正确识别流式响应
            response = Response(generate_stream(), mimetype='text/event-stream')
            response.headers['Cache-Control'] = 'no-cache'
            response.headers['Connection'] = 'keep-alive'
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            return response
        else:
            response = model.generate_content(
                contents,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            finish_reason = 'stop'
            if response.candidates and response.candidates[0].finish_reason:
                fr_name = response.candidates[0].finish_reason.name
                if fr_name == 'MAX_TOKENS':
                    finish_reason = 'length'
                elif fr_name == 'SAFETY':
                    finish_reason = 'content_filter'
            
            response_data = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response.text
                        },
                        "finish_reason": finish_reason
                    }
                ],
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
            }
            return jsonify(response_data)
            
    except Exception as e:
        return jsonify({"error": f"服务器错误: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Gemini Vertex AI代理服务启动中...")
    print(f"📍 服务地址: http://localhost:{port}/v1/chat/completions")
    print(f"🔧 调试模式: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 