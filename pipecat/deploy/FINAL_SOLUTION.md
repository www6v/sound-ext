# 麦克风验证 - 最终解决方案

## 问题
文字模式和麦克风都无法工作，因为：
1. 前端使用 WebSocket 通信
2. 简单的 HTTP 代理不支持 WebSocket
3. WebSocket 代理需要 websockets 模块

## 当前状态
- ✅ 服务器 HTTPS 正常 (100.94.242.79:8443)
- ✅ HTTP 代理正常 (localhost:8032)
- ✅ 麦克风权限已设置 (localhost:8032 = 允许)
- ❌ WebSocket 代理未运行（websockets 模块安装问题）

## 解决方案

### 方案 1：在客户端手动安装并运行（推荐）

在客户端机器 (100.126.13.38) 上运行：

```bash
# 1. 安装 websockets
pip3 install websockets --user --break-system-packages

# 2. 停止旧代理
fuser -k 8032/tcp 2>/dev/null
sleep 2

# 3. 运行完整代理
nohup python3 /tmp/fixed_proxy.py > /tmp/fixed_proxy.log 2>&1 &

# 4. 测试
curl -s http://localhost:8032/health

# 5. 打开 Firefox
firefox http://localhost:8032
```

### 方案 2：使用 Realtime-Venus 的方式

既然 Realtime-Venus (localhost:8032) 的麦克风可以工作，直接修改我们的前端代码，让它连接到 Realtime-Venus 的服务器。

### 方案 3：直接在服务器上用 HTTPS

在客户端 Firefox 中直接访问：
```
https://100.94.242.79:8443
```
接受证书警告。但这可能无法使用麦克风（非 localhost）。

## 关键文件

- 代理脚本：`/tmp/fixed_proxy.py`（在客户端）
- 支持 HTTP + WebSocket
- 端口：8032

## 验证步骤

1. 确保代理运行：`curl -s http://localhost:8032/health`
2. 打开 Firefox：`firefox http://localhost:8032`
3. 点击"语音模式"
4. 测试麦克风

## 麦克风权限

Firefox 中已设置：
- `http://localhost:8032` = 允许
