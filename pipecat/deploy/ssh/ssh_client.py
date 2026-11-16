#!/usr/bin/env python3
"""
SSH 连接工具
连接到客户端机器并执行命令
"""
import pexpect
import sys
import time

class SSHClient:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.child = None

    def connect(self):
        """建立 SSH 连接"""
        print(f"连接到 {self.user}@{self.host}...")
        self.child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {self.user}@{self.host}')
        self.child.expect('password:', timeout=10)
        self.child.sendline(self.password)
        self.child.expect(r'\$|>', timeout=10)
        print("✓ 连接成功")

    def run(self, command, timeout=30):
        """运行命令"""
        self.child.sendline(command)
        self.child.expect(r'\$|>', timeout=timeout)
        return self.child.before.decode('utf-8', errors='ignore').strip()

    def close(self):
        """关闭连接"""
        if self.child:
            self.child.sendline('exit')
            self.child.expect(pexpect.EOF)
            print("✓ 连接已关闭")

def main():
    # 配置
    HOST = '100.126.13.38'
    USER = 'wangwei'
    PASSWORD = '123wazxc'

    # 连接
    client = SSHClient(HOST, USER, PASSWORD)
    client.connect()

    # 执行命令
    commands = [
        ('pip3 install websockets --user --break-system-packages -q', '安装 websockets'),
        ('fuser -k 8032/tcp 2>/dev/null; sleep 2', '停止旧进程'),
        ('nohup python3 /tmp/fixed_proxy.py > /tmp/fixed_proxy.log 2>&1 &', '启动代理'),
        ('sleep 3', '等待'),
        ('curl -s http://localhost:8032/health', '测试代理'),
        ('firefox http://localhost:8032 &', '打开 Firefox'),
    ]

    for cmd, desc in commands:
        print(f"\n{desc}...")
        result = client.run(cmd, timeout=120)
        if desc == '测试代理':
            print(f"  结果: {result}")
            if '"status":"ok"' in result:
                print("  ✓ 代理正常!")
            else:
                print("  ✗ 代理失败")
        time.sleep(1)

    print("\n" + "="*70)
    print("完成！请在客户端 Firefox 中:")
    print("1. 刷新 http://localhost:8032")
    print("2. 点击'语音模式'")
    print("3. 测试麦克风")
    print("="*70)

    client.close()

if __name__ == '__main__':
    main()
