"""统一路径解析：兼容源码运行与 PyInstaller 打包后的单文件 exe。

关键：数据必须落在 exe 同目录（不是临时解压目录），否则关掉软件数据就没了。
"""
import os
import sys

FROZEN = getattr(sys, "frozen", False)
BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def app_dir():
    """exe 所在目录（打包）/ 脚本所在目录（源码）。"""
    if FROZEN:
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """用户数据目录，可用 OPEN_TUTOR_DATA_DIR 覆盖。"""
    env = os.environ.get("OPEN_TUTOR_DATA_DIR")
    if env:
        return env
    return os.path.join(app_dir(), "data")


def static_dir():
    """前端静态资源目录。打包后从临时解压目录读。"""
    return os.path.join(BUNDLE_DIR, "static")
