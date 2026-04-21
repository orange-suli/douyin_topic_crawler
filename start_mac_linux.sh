#!/bin/bash

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}======================================================"
echo -e "   欢迎使用抖音多维度数据抓取与分析看板系统"
echo -e "======================================================${NC}"
echo

# 1. 检查 Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未检测到 python3，请前往 https://www.python.org/ 下载安装。${NC}"
    exit 1
fi

# 2. 创建并激活虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[*] 正在创建虚拟环境 (venv)...${NC}"
    python3 -m venv venv
fi

echo -e "${YELLOW}[*] 正在激活虚拟环境...${NC}"
source venv/bin/activate

# 3. 安装依赖
echo -e "${YELLOW}[*] 正在安装依赖包...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 4. 安装 Playwright
echo -e "${YELLOW}[*] 确保浏览器内核已安装...${NC}"
playwright install chromium

# 5. 启动服务
echo
echo -e "${GREEN}[!] 正在启动后端服务...${NC}"

# 在后台启动后端
python3 -m backend.main &
BACKEND_PID=$!

# 6. 等待启动并打开浏览器
sleep 3
echo -e "${YELLOW}[*] 正在打开系统默认浏览器...${NC}"

if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000
else
    xdg-open http://localhost:8000 || echo -e "${YELLOW}[提示] 请手动打开: http://localhost:8000${NC}"
fi

echo
echo -e "${GREEN}======================================================"
echo -e "    服务已启动 (PID: $BACKEND_PID)！"
echo -e "    本地访问地址: http://localhost:8000"
echo -e "    若要停止服务，请按 Ctrl+C"
echo -e "======================================================${NC}"
echo

# 等待后台进程
wait $BACKEND_PID
