#!/usr/bin/env python3
"""
简单的 SSL 隧道客户端
将本地 localhost:8000 转发到远程 HTTPS 服务器
"""

import socket
import ssl
import threading
import sys

REMOTE_HOST = '100.94.242.79'
REMOTE_PORT = 8443
LOCAL_PORT = 8000

def forward(src, dst):
    """双向数据转发"""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception as e:
        pass
    finally:
        try:
            src.close()
            dst.close()
        except:
            pass

def handle_client(client_socket):
    """处理客户端连接"""
    try:
        # 创建到远程服务器的 SSL 连接
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        remote_ssl = context.wrap_socket(remote_socket, server_hostname=REMOTE_HOST)
        remote_ssl.connect((REMOTE_HOST, REMOTE_PORT))

        # 双向转发
        threading.Thread(target=forward, args=(client_socket, remote_ssl)).start()
        threading.Thread(target=forward, args=(remote_ssl, client_socket)).start()

    except Exception as e:
        print(f"错误: {e}")
        client_socket.close()

def main():
    """主函数"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('localhost', LOCAL_PORT))
    server.listen(5)

    print(f"隧道已启动: http://localhost:{LOCAL_PORT} -> https://{REMOTE_HOST}:{REMOTE_PORT}")
    print(f"在浏览器中访问: http://localhost:{LOCAL_PORT}")
    print("按 Ctrl+C 停止")

    try:
        while True:
            client, addr = server.accept()
            print(f"新连接: {addr}")
            threading.Thread(target=handle_client, args=(client,)).start()
    except KeyboardInterrupt:
        print("\n停止隧道")
        server.close()

if __name__ == '__main__':
    main()
