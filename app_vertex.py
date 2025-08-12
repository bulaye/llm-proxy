from flask import Flask, request, jsonify, Response
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