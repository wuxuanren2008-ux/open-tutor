"""OpenTutor 桌面版入口：内置本地服务 + Edge 独立应用窗口（无地址栏，像普通软件）。

双击 OpenTutor.exe 后：
1. 在后台线程启动本地 HTTP 服务（自动选空闲端口）
2. 用 Edge --app 模式打开一个独立窗口，没有地址栏和标签页
3. 关掉窗口时，程序自动退出
数据存在 exe 同目录的 data/ 下，关掉重开不会丢。
"""
import os
import subprocess
import sys
import threading
import time

import paths
import server
import store

# --windowed 打包后 stdout/stderr 是 None，print 会崩。重定向到数据目录的日志文件。
if sys.stdout is None or sys.stderr is None:
    os.makedirs(paths.data_dir(), exist_ok=True)
    _log = open(os.path.join(paths.data_dir(), "run.log"), "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log
    if sys.stderr is None:
        sys.stderr = _log


def log(msg):
    print(msg, flush=True)


def find_edge():
    """找 Edge 可执行文件；找不到就退回系统默认浏览器。"""
    candidates = [
        os.environ.get("OPEN_TUTOR_EDGE", ""),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def main():
    os.makedirs(paths.data_dir(), exist_ok=True)
    store.init()

    # 启动内置服务，拿实际端口
    httpd, port = server.pick_server(server.PORT)
    url = "http://127.0.0.1:%d/" % port
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # 独立用户目录，避免和用户日常 Edge 混在一起、也避免被已有实例吞掉参数
    profile = os.path.join(paths.data_dir(), "edge-profile")
    edge = find_edge()
    if edge:
        args = [
            edge,
            "--app=" + url,
            "--user-data-dir=" + profile,
            "--window-size=1180,820",
            "--window-position=120,80",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=TranslateUI",
        ]
        try:
            proc = subprocess.Popen(args)
            log("OpenTutor: 已在独立窗口打开 " + url)
            # 窗口关闭后退出程序
            while proc.poll() is None:
                time.sleep(0.5)
        except OSError:
            import webbrowser
            webbrowser.open(url)
    else:
        import webbrowser
        webbrowser.open(url)
        log("OpenTutor: 已用默认浏览器打开 " + url)
        # 无 Edge 时保持服务常驻，用户手动关窗口
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    httpd.shutdown()
    log("OpenTutor: 已退出。")


if __name__ == "__main__":
    main()
