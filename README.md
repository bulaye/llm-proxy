# Gemini 代理服务

这是一个将 OpenAI API 格式转换为 Google Vertex AI Gemini API 的代理服务。

## 功能特性

- 支持文本和多模态对话
- 支持流式和非流式响应
- 支持 Base64 图片和远程图片 URL
- 完整的 OpenAI 兼容 API

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `env.example` 为 `.env` 并配置：

```bash
cp env.example .env
```

编辑 `.env` 文件：

```env
# Google Cloud配置
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# 服务配置
PORT=8080
DEBUG=True

# Google Cloud认证（选择其中一种方式）
# 方式1: API Key
GOOGLE_API_KEY="your-api-key"

# 方式2: 服务账号密钥文件
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

### 3. Google Cloud 认证设置

#### 方式 1: 使用 API Key （推荐）

1. 在 Google Cloud Console 中创建 API Key
2. 启用 Vertex AI API
3. 将 API Key 设置到环境变量 `GOOGLE_API_KEY`

#### 方式 2: 使用服务账号

1. 创建服务账号并下载 JSON 密钥文件
2. 设置环境变量 `GOOGLE_APPLICATION_CREDENTIALS` 指向该文件
3. 确保服务账号有 Vertex AI 权限

#### 方式 3: 使用 gcloud CLI

```bash
gcloud auth login
gcloud config set project your-project-id
```

## 运行服务

```bash
python app_vertex.py
```

服务将在 `http://localhost:8080` 启动。

## API 使用

### 健康检查

```bash
curl http://localhost:8080/health
```

### 文本对话

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### 多模态对话（图片）

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "What is in this image?"},
          {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGg..."}}
        ]
      }
    ]
  }'
```

## 故障排除

### 1. 连接超时错误 (503 timeout)

**错误**: `"503 failed to connect to all addresses; last error: UNAVAILABLE: ipv4:xxx:443: Failed to connect to remote host: Timeout occurred: FD shutdown"`

**解决方案**:

- 检查网络连接
- 确认已正确配置 Google Cloud 认证
- 验证项目 ID 和区域设置是否正确
- 确保已启用 Vertex AI API

### 2. 图片处理错误

**错误**: `"Image() takes no arguments"`

**解决方案**: 已修复 - 现在使用 `Image.load_from_file()` 方法和临时文件处理

### 3. 认证问题

**错误**: 认证相关错误

**解决方案**:

1. 确认环境变量设置正确
2. 检查 API Key 或服务账号权限
3. 运行 `gcloud auth list` 检查当前认证状态

### 4. 项目或区域配置问题

**解决方案**:

1. 确认项目 ID 正确: `gcloud config get-value project`
2. 确认区域设置为 `us-central1`（Vertex AI 主要区域）
3. 检查项目是否启用了 Vertex AI API

## 开发和测试

### 运行测试

```bash
python test_client.py
```

### Docker 部署

```bash
docker build -t gemini-proxy .
docker run -p 8080:8080 --env-file .env gemini-proxy
```

## 支持的模型

- gemini-2.5-pro
- gemini-2.5-flash
- gemini-1.5-pro
- gemini-1.5-flash

## 注意事项

1. 确保 Google Cloud 项目已启用 Vertex AI API
2. 建议使用 `us-central1` 区域以获得最佳性能
3. Base64 图片会被转换为临时文件进行处理
4. 服务支持 CORS，可以从浏览器直接调用
