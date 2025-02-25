@echo off
echo 正在检查 Python 虚拟环境...

if not exist ".venv" (
    echo 正在创建虚拟环境...
    python -m venv .venv
)

echo 正在激活虚拟环境...
call .venv\Scripts\activate.bat

echo 正在安装依赖项...
pip install -r requirements.txt

echo 启动应用程序...
python app.py

pause