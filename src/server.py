#!/usr/bin/env python3
"""
GhostRadio Trigger Server - 极简 Webhook 接收器
内存占用目标: < 15MB
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 配置
QUEUE_FILE = "queue.txt"
HOST = "0.0.0.0"
PORT = 8080


class WebhookHandler(BaseHTTPRequestHandler):
    """处理 Webhook 请求的处理器"""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")
    
    def do_GET(self):
        """处理 GET 请求 - 健康检查和简单页面"""
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "ghostradio-trigger"})
        elif self.path == "/":
            self._send_html(200, self._get_index_page())
        else:
            self._send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        """处理 POST 请求 - 接收 URL"""
        if self.path == "/webhook":
            self._handle_webhook()
        else:
            self._send_json(404, {"error": "Not found"})
    
    def _handle_webhook(self):
        """处理 Webhook - 接收 URL 并写入队列"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json(400, {"error": "Empty request body"})
                return
            
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # 解析 JSON
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                # 尝试作为纯文本 URL 处理
                data = {"url": post_data.strip()}
            
            url = data.get('url', '').strip()
            
            if not url:
                self._send_json(400, {"error": "Missing 'url' parameter"})
                return
            
            # 验证 URL 格式
            if not url.startswith(('http://', 'https://')):
                self._send_json(400, {"error": "Invalid URL format"})
                return
            
            # 写入队列文件
            timestamp = datetime.now().isoformat()
            queue_entry = f"{timestamp}|{url}\n"
            
            with open(QUEUE_FILE, 'a', encoding='utf-8') as f:
                f.write(queue_entry)
            
            self.log_message("Added to queue: %s", url[:60])
            self._send_json(200, {
                "success": True,
                "message": "URL added to queue",
                "url": url[:100] + "..." if len(url) > 100 else url
            })
            
        except Exception as e:
            self.log_message("Error: %s", str(e))
            self._send_json(500, {"error": str(e)})
    
    def _send_json(self, status_code, data):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_html(self, status_code, html):
        """发送 HTML 响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _get_index_page(self):
        """返回简单的首页 HTML"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>GhostRadio Trigger</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .endpoint { background: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace; }
        .example { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; }
        code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
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
        <code>curl -X POST http://localhost:8080/webhook \\<br>
        -H "Content-Type: application/json" \\<br>
        -d '{"url": "https://example.com/article"}'</code>
    </div>
    
    <h2>健康检查</h2>
    <div class="endpoint">
        GET /health - 服务状态检查
    </div>
    
    <p><small>GhostRadio - 极致省资源的播客生成器</small></p>
</body>
</html>"""


def run_server():
    """启动服务器"""
    server = HTTPServer((HOST, PORT), WebhookHandler)
    print(f"GhostRadio Trigger Server started at http://{HOST}:{PORT}")
    print(f"Queue file: {QUEUE_FILE}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
