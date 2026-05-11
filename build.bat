@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === MC 传送点记录工具 - 打包 ===
echo.

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
)

echo 开始打包...
pyinstaller --onefile --noconsole --clean --name MC_Teleport_Tool teleport_tool.py

echo.
echo 打包完成! 输出文件: dist\MC_Teleport_Tool.exe
pause
