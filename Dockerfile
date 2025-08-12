# 使用 Python 3.11 作为基础镜像
FROM python:3.11-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app_vertex.py \
    FLASK_ENV=production \
    FLASK_DEBUG=false \
    DEBUG=false \
    PORT=8080 \
    GOOGLE_CLOUD_PROJECT=bulayezhou \
    GOOGLE_CLOUD_LOCATION=us-central1

# 安装系统依赖
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    curl

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN adduser -D -s /bin/sh app && \
    chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动应用
CMD ["python", "app_vertex.py"] 