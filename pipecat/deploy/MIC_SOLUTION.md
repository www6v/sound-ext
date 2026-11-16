# 麦克风验证 - 最终解决方案

## 问题
需要在客户端 Firefox 中验证麦克风是否工作，但无法自动化建立 SSH 隧道。

## 原因分析

Realtime-Venus demo 可以工作的原因：
- 它通过 `http://localhost:8032` 访问
- `localhost` 是安全上下文
- 麦克风 API 可以正常工作

我们的问题：
- 服务器在 100.94.242.79:8443
- 客户端通过 Tailscale IP 访问（不是 localhost）
- 需要 SSH 隧道将远程端口转发到本地 localhost

## 解决方案

### 在客户端机器 (100.126.13.38) 上手动操作：

#### 步骤 1：打开终端

#### 步骤 2：建立 SSH 隧道
```bash
ssh -L 8000:100.94.242.79:8443 wangwei@100.94.242.79
```
输入密码：`123wazxc`

保持终端打开。

#### 步骤 3：验证隧道
```bash
curl -s http://localhost:8000/health
```
应该返回：`{"status":"ok","llm":true,"tts":true}`

#### 步骤 4：打开 Firefox
```bash
firefox http://localhost:8000
```

#### 步骤 5：测试麦克风
1. 点击"语音模式"按钮
2. 如果弹出麦克风权限请求，点击"允许"
3. 对着麦克风说话
4. 应该能看到语音识别结果

## 为什么必须用 localhost？

浏览器安全策略：
- `localhost` = 安全上下文 ✅ 麦克风可用
- `http://100.x.x.x` = 不安全上下文 ❌ 麦克风不可用
- `https://...` = 安全上下文 ✅ 但需要有效证书

## 故障排查

### 问题 1：隧道连接失败
```bash
# 检查服务器
ssh wangwei@100.94.242.79
curl -sk https://localhost:8443/health
```

### 问题 2：麦克风无法访问
1. Firefox 地址栏输入 `about:preferences#privacy`
2. 滚动到"权限" → "麦克风"
3. 确保 `http://localhost:8000` 被允许

### 问题 3：页面无法访问
```bash
# 检查隧道进程
ps aux | grep ssh | grep 8000

# 检查端口
ss -tlnp | grep 8000
```

## 快速测试命令

```bash
# 一行命令建立隧道并打开 Firefox
ssh -L 8000:100.94.242.79:8443 wangwei@100.94.242.79 -N &
sleep 3
firefox http://localhost:8000
```

## 参考

Realtime-Venus demo 也是通过 localhost 访问实现麦克风功能的。
