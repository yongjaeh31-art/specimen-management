"""
검체관리프로그램 런처
더블클릭 → 서버 시작 → 브라우저 자동 오픈
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser

PORT = 8000
URL  = f"http://localhost:{PORT}"


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _server_ready(timeout: float = 25) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", PORT), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def _already_running() -> bool:
    try:
        with socket.create_connection(("localhost", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def main():
    # 이미 서버가 켜진 경우 → 브라우저만 열기
    if _already_running():
        webbrowser.open(URL)
        return

    app_dir    = _app_dir()
    python_exe = os.path.join(app_dir, "python", "python.exe")

    if not os.path.isfile(python_exe):
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"python\\python.exe를 찾을 수 없습니다.\n경로: {python_exe}",
            "검체관리프로그램 오류",
            0x10,
        )
        return

    # 콘솔 창 숨기고 uvicorn 시작
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0   # SW_HIDE

    server = subprocess.Popen(
        [
            python_exe, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(PORT),
        ],
        cwd=app_dir,
        startupinfo=si,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # 서버 준비 대기 후 브라우저 오픈
    if _server_ready(timeout=30):
        webbrowser.open(URL)
    else:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "서버 시작에 실패했습니다.\n로그를 확인하거나 관리자에게 문의하세요.",
            "검체관리프로그램 오류",
            0x10,
        )
        server.terminate()
        return

    # 서버 프로세스가 끝날 때까지 런처 유지
    server.wait()


if __name__ == "__main__":
    main()
