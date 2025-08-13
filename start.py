#!/usr/bin/env python3
"""
统一启动脚本 - 支持开发和生产模式
"""
import os
import sys
import subprocess

def start_development():
    """启动开发服务器"""
    from app_vertex import app
    
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print(f"🚀 Gemini Vertex AI代理服务启动中...")
    print(f"📍 服务地址: http://localhost:{port}/v1/chat/completions")
    print(f"🔧 开发模式: Flask 开发服务器")
    print(f"🐛 调试模式: {debug}")
    print(f"⚠️  注意: 这是开发服务器，不要在生产环境中使用")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

def start_production():
    """启动生产服务器"""
    port = int(os.getenv('PORT', 8080))
    workers = int(os.getenv('GUNICORN_WORKERS', 4))
    timeout = int(os.getenv('GUNICORN_TIMEOUT', 6000))
    
    print(f"🚀 Gemini Vertex AI代理服务启动中...")
    print(f"📍 服务地址: http://localhost:{port}/v1/chat/completions")
    print(f"🔧 生产模式: Gunicorn WSGI 服务器")
    print(f"👥 工作进程: {workers}")
    print(f"⏱️  超时时间: {timeout}秒")
    
    gunicorn_args = [
        'gunicorn',
        '--bind', f'0.0.0.0:{port}',
        '--workers', str(workers),
        '--timeout', str(timeout),
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info',
        '--preload',
        'app_vertex:app'
    ]
    
    try:
        subprocess.run(gunicorn_args, check=True)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        # 根据环境变量决定模式
        mode = os.getenv('FLASK_ENV', 'development').lower()
    
    if mode in ['prod', 'production', 'p']:
        start_production()
    elif mode in ['dev', 'development', 'd']:
        start_development()
    else:
        print("使用方法:")
        print("  python start.py dev     # 开发模式 (Flask 开发服务器)")
        print("  python start.py prod    # 生产模式 (Gunicorn WSGI 服务器)")
        print("")
        print("环境变量:")
        print("  FLASK_ENV=development   # 开发模式")
        print("  FLASK_ENV=production    # 生产模式")
        print("  PORT=8080              # 端口号")
        print("  DEBUG=True/False       # 调试模式")

if __name__ == '__main__':
    main() 