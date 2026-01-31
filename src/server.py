#!/usr/bin/env python3
"""
GhostRadio Trigger Server - 极简 Webhook 接收器
内存占用目标: < 15MB
"""

import os
import sys
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import get_config
from src.api_routes import handle_api_request


def get_server_config() -> Dict[str, Any]:
    """从配置文件获取服务器配置"""
    try:
        config = get_config()
        paths = config.get_paths_config()
        return {
            'queue_file': paths.get('queue_file', 'queue.txt'),
            'host': config.get('server.host', '0.0.0.0'),
            'port': config.get('server.port', 8080, int)
        }
    except Exception:
        return {
            'queue_file': 'queue.txt',
            'host': '0.0.0.0',
            'port': 8080
        }


class WebhookHandler(BaseHTTPRequestHandler):
    """处理 Webhook 请求的处理器"""

    config: Dict[str, Any] = {}

    def log_message(self, format: str, *args) -> None:
        """自定义日志格式"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _send_html(self, status_code: int, html: str) -> None:
        """发送 HTML 响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _get_index_page(self) -> str:
        """返回简单的首页 HTML"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>GhostRadio Trigger</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .endpoint {{ background: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace; }}
        .example {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>GhostRadio Trigger Server</h1>
    <p>极简 Webhook 接收器 - 平时"装死"，只在有任务时"诈尸"</p>

    <h2>API 端点</h2>
    <div class="endpoint">
        POST /webhook - 提交 URL 到处理队列
    </div>

    <h3>请求示例</h3>
    <div class="example">
        <code>curl -X POST http://localhost:{self.config.get('port', 8080)}/webhook \\<br>
        -H "Content-Type: application/json" \\<br>
        -d '{{"url": "https://example.com/article"}}'</code>
    </div>

    <h2>健康检查</h2>
    <div class="endpoint">
        GET /health - 服务状态检查
    </div>

    <p><small>GhostRadio - 极致省资源的播客生成器</small></p>
</body>
</html>"""

    def do_GET(self) -> None:
        """处理 GET 请求"""
        # API 路由
        if self.path.startswith('/api/'):
            status_code, data, content_type = handle_api_request(self, self.path, 'GET')
            self._send_response(status_code, data, content_type)
            return
        
        # 静态文件服务
        if self.path.startswith('/episodes/'):
            self._serve_static_file(self.path[1:])  # 移除开头的 /
            return
        
        # 页面路由
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "ghostradio-trigger"})
        elif self.path == "/":
            # 返回新的前端页面
            self._serve_index_page()
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        """处理 POST 请求"""
        # API 路由
        if self.path.startswith('/api/'):
            status_code, data, content_type = handle_api_request(self, self.path, 'POST')
            self._send_response(status_code, data, content_type)
            return
        
        # Webhook 路由
        if self.path == "/webhook":
            self._handle_webhook()
        else:
            self._send_json(404, {"error": "Not found"})

    def _handle_webhook(self) -> Optional[Dict[str, Any]]:
        """处理 Webhook - 接收 URL 并写入队列"""
        try:
            content_length: int = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json(400, {"error": "Empty request body"})
                return None

            post_data: str = self.rfile.read(content_length).decode('utf-8')

            try:
                data: Dict[str, Any] = json.loads(post_data)
            except json.JSONDecodeError:
                data = {"url": post_data.strip()}

            url: str = data.get('url', '').strip()

            if not url:
                self._send_json(400, {"error": "Missing 'url' parameter"})
                return None

            if not url.startswith(('http://', 'https://')):
                self._send_json(400, {"error": "Invalid URL format"})
                return None

            timestamp: str = datetime.now().isoformat()
            queue_entry: str = f"{timestamp}|{url}\n"

            queue_file: str = self.config.get('queue_file', 'queue.txt')
            with open(queue_file, 'a', encoding='utf-8') as f:
                f.write(queue_entry)

            self.log_message("Added to queue: %s", url[:60])
            self._send_json(200, {
                "success": True,
                "message": "URL added to queue",
                "url": url[:100] + "..." if len(url) > 100 else url
            })
            return {"success": True, "url": url}

        except json.JSONDecodeError as e:
            self.log_message("JSON decode error: %s", str(e))
            self._send_json(400, {"error": f"Invalid JSON: {str(e)}"})
            return None
        except IOError as e:
            self.log_message("IO error: %s", str(e))
            self._send_json(500, {"error": f"Failed to write queue: {str(e)}"})
            return None
        except Exception as e:
            self.log_message("Unexpected error: %s", str(e))
            self._send_json(500, {"error": str(e)})
            return None

    def _send_response(self, status_code: int, data: Any, content_type: str) -> None:
        """发送通用响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        
        if content_type == 'application/json':
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        else:
            self.wfile.write(str(data).encode('utf-8'))

    def _serve_static_file(self, file_path: str) -> None:
        """提供静态文件服务"""
        try:
            path = Path(file_path)
            if not path.exists():
                self._send_json(404, {"error": "File not found"})
                return
            
            # 根据文件扩展名设置 Content-Type
            content_type = 'application/octet-stream'
            if path.suffix == '.mp3':
                content_type = 'audio/mpeg'
            elif path.suffix == '.html':
                content_type = 'text/html'
            elif path.suffix == '.css':
                content_type = 'text/css'
            elif path.suffix == '.js':
                content_type = 'application/javascript'
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(path.stat().st_size))
            self.end_headers()
            
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _serve_index_page(self) -> None:
        """提供前端页面"""
        try:
            index_path = Path("episodes/index.html")
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._send_html(200, content)
            else:
                # 返回默认的简单页面
                self._send_html(200, self._get_index_page())
        except Exception as e:
            self._send_json(500, {"error": str(e)})


def run_server() -> None:
    """启动服务器"""
    config = get_server_config()
    host: str = config['host']
    port: int = config['port']
    queue_file: str = config['queue_file']

    WebhookHandler.config = config

    server = HTTPServer((host, port), WebhookHandler)
    print(f"GhostRadio Trigger Server started at http://{host}:{port}")
    print(f"Queue file: {queue_file}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GhostRadio Trigger Server')
    parser.add_argument('--config', '-c', default='config.yaml', help='Config file path')
    args = parser.parse_args()

    from src.config import reload_config
    reload_config(args.config)

    run_server()
