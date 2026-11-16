# 麦克风验证 - 最终指南

## 问题
- 文字模式和麦克风都无法工作
- 原因：前端使用 WebSocket，HTTP 代理不支持 WebSocket
- 需要运行支持 WebSocket 的代理

## 解决方案

### 在客户端机器 (100.126.13.38) 上运行以下命令：

```bash
# 1. 安装 websockets
pip3 install websockets --user --break-system-packages

# 2. 停止占用 8032 端口的进程
fuser -k 8032/tcp 2>/dev/null
sleep 2

# 3. 运行完整代理（HTTP + WebSocket）
nohup python3 /tmp/fixed_proxy.py > /tmp/fixed_proxy.log 2>&1 &

# 4. 等待代理启动
sleep 3

# 5. 测试代理
curl -s http://localhost:8032/health
# 应该返回: {"status":"ok","llm":true,"tts":true}

# 6. 打开 Firefox
firefox http://localhost:8032
```

### 然后在 Firefox 中：

1. **刷新页面** (Ctrl+R 或 F5)
2. **点击"语音模式"** 按钮
3. **测试麦克风** - 对着麦克风说话

### 麦克风权限

Firefox 中已设置 `http://localhost:8032` 的麦克风权限为"允许"。

## 关键信息

- **代理脚本**: `/tmp/fixed_proxy.py`（已复制到客户端）
- **端口**: 8032（HTTP + WebSocket）
- **麦克风权限**: 已设置为"允许"
- **参考**: Realtime-Venus 使用相同的端口 (8032)，麦克风可以工作

## 故障排查

### 问题 1：端口被占用
```bash
fuser -k 8032/tcp
sleep 2
nohup python3 /tmp/fixed_proxy.py > /tmp/fixed_proxy.log 2>&1 &
```

### 问题 2：代理启动失败
```bash
cat /tmp/fixed_proxy.log
# 检查错误信息
```

### 问题 3：麦克风无法访问
1. Firefox 地址栏输入 `about:preferences#privacy`
2. 滚动到"权限" → "麦克风"
3. 确保 `http://localhost:8032` 状态是"允许"

## 为什么这样可以工作？

1. **localhost 是安全上下文** - 浏览器允许麦克风访问
2. **端口 8032** - 和 Realtime-Venus 一样，麦克风权限已设置
3. **WebSocket 支持** - 代理支持 WebSocket，前端可以正常通信
4. **HTTP + WebSocket** - 统一代理处理所有请求
