#!/bin/bash
# 启动 HTTPS 服务器

cd "$(dirname "$0")"

# 激活虚拟环境
source .venv/bin/activate

# 加载环境变量
if [ -f "../.env" ]; then
    export $(grep -v '^#' ../.env | xargs)
fi

# 检查证书
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "生成自签名证书..."
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=192.168.3.4" 2>/dev/null
fi

# 停止旧服务器
pkill -f "server_simple.py" 2>/dev/null
sleep 1

echo "=================================================="
echo "  启动 HTTPS 服务器"
echo "=================================================="
echo ""
echo "访问地址: https://192.168.3.4:8443"
echo ""
echo "注意: 浏览器会提示证书不安全，点击"高级" -> "继续访问""
echo ""

# 启动 HTTPS 服务器
python server_simple.py --ssl-certfile cert.pem --ssl-keyfile key.pem --port 8443
