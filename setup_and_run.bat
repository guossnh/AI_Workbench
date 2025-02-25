@echo off
echo 正在初始化环境，请稍候...

IF NOT EXIST ".venv" (
    echo 创建虚拟环境...
    python -m venv .venv
)

echo 激活虚拟环境...
 call .venv\Scripts\activate.bat

echo 安装依赖包...
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

echo 启动应用程序...
python app.py

pause