"""
康孪生 HealthTwin 桌面版启动器（exe 入口）

双进程架构（PyInstaller 打包后的经典做法）：
  主模式（双击 exe）：
    1. 找一个空闲端口，以隐藏窗口重新拉起自己（--worker 模式）跑 Streamlit 服务
    2. 轮询 /_stcore/health 直到服务就绪
    3. 用 pywebview 弹出原生应用窗口加载本机页面；退出窗口即结束整个应用
       （pywebview 不可用时自动降级为打开系统浏览器）
  --worker 模式（子进程）：直接在本进程内运行 Streamlit CLI
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))
if IS_FROZEN:
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    APP_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent.parent
    APP_DIR = RESOURCE_DIR

APP_PY = RESOURCE_DIR / "app.py"
START_TIMEOUT = 90  # 首次启动（冷启动 + 杀软扫描）最多少秒


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_worker(port: int) -> None:
    """子进程模式：在本进程内跑 Streamlit（app.py 与用户数据见 launcher 顶部注释）。"""
    os.chdir(APP_DIR)  # data/ 落在 exe 旁边
    # 打包环境里 streamlit/config.py 不在 site-packages，会被误判为"开发模式"，
    # 进而禁止自定义端口 —— 必须用 CLI 参数显式关闭
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit", "run", str(APP_PY),
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--server.port", str(port),
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
        "--theme.base", "light",
        "--theme.primaryColor", "#2563EB",
        "--theme.backgroundColor", "#FFFFFF",
        "--theme.secondaryBackgroundColor", "#F5F7FA",
        "--theme.textColor", "#1F2937",
    ]
    stcli.main()


def wait_ready(port: int) -> bool:
    url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.time() + START_TIMEOUT
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.read().strip() == b"ok":
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    port = free_port()
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        [sys.executable, "--worker", "--port", str(port)],
        cwd=str(APP_DIR),
        creationflags=creationflags,
    )

    if not wait_ready(port):
        proc.terminate()
        print("服务启动超时，请联系提供者。", file=sys.stderr)
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    try:
        import webview  # pywebview

        icon = RESOURCE_DIR / "app_icon.ico"
        webview.create_window(
            "康孪生 HealthTwin",
            url,
            width=1280,
            height=840,
            min_size=(980, 640),
            icon=str(icon) if icon.exists() else None,
        )
        webview.start()
    except Exception:
        # 无 WebView2 运行时等场景：退化为系统浏览器
        import webbrowser
        webbrowser.open(url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--worker" in args:
        run_worker(int(args[args.index("--port") + 1]))
    else:
        main()
