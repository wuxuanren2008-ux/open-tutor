"""跨平台启动脚本：自动选 Python，跑自检提示，然后启动服务。"""
import subprocess
import sys


def main():
    print("=" * 46)
    print(" OpenTutor - 开源 AI 导学助手")
    print("=" * 46)
    print("启动后浏览器打开: http://127.0.0.1:8766")
    print("按 Ctrl+C 停止。\n")
    try:
        subprocess.run([sys.executable, "server.py"], check=True)
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
