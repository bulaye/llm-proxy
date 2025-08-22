FROM nginx:stable-alpine

# 将你的 nginx.conf 文件复制到容器的正确位置
# 这个操作会覆盖掉 Nginx 镜像中默认的配置
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露 8080 端口，以便容器可以接收 HTTP 请求
EXPOSE 8080

# 启动 nginx 服务
CMD ["nginx", "-g", "daemon off;"]