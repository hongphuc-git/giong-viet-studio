"""Portable launcher and loopback-only server. No cloud upload or installation."""
import base64
import json
import math
import mimetypes
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
PROCESS: subprocess.Popen | None = None
LOG_HANDLE = None
STATE_PATH: Path | None = None
STATE: dict[str, str | int | float] = {'status': 'idle', 'message': 'Sẵn sàng tạo giọng đọc', 'percent': 0}


def current_state() -> dict[str, str | int | float]:
    global STATE, PROCESS, LOG_HANDLE
    with LOCK:
        if PROCESS is not None:
            if STATE_PATH is not None and STATE_PATH.exists():
                try:
                    candidate = json.loads(STATE_PATH.read_text(encoding='utf-8'))
                    if isinstance(candidate, dict):
                        STATE = candidate
                except (OSError, ValueError):
                    pass
            result = PROCESS.poll()
            if result is not None:
                if LOG_HANDLE is not None:
                    LOG_HANDLE.close()
                    LOG_HANDLE = None
                if result != 0 or STATE.get('status') != 'completed':
                    STATE = {'status': 'failed', 'message': 'Không tạo được âm thanh. Xem logs trong thư mục ứng dụng để biết chi tiết.', 'percent': 0}
                PROCESS = None
        return dict(STATE)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, template: str, *args: object) -> None:
        pass

    def respond(self, code: int, payload: object) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def authorized(self) -> bool:
        supplied = self.headers.get('X-Session-Token', '')
        return secrets.compare_digest(supplied, TOKEN)

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path == '/api/status':
            if not self.authorized():
                self.respond(403, {'error': 'Hãy mở giao diện bằng file EXE.'})
                return
            self.respond(200, current_state())
            return
        if path.startswith('/audio/'):
            directory = ROOT / 'outputs'
            file = directory / Path(path).name
        else:
            directory = ROOT / 'web'
            file = directory / (path.lstrip('/') or 'index.html')
        if not file.resolve().is_relative_to(directory.resolve()) or not file.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(file.stat().st_size))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        if path.startswith('/audio/') and urlsplit(self.path).query == 'download=1':
            self.send_header('Content-Disposition', f'attachment; filename="{file.name}"')
        self.end_headers()
        try:
            with file.open('rb') as stream:
                while chunk := stream.read(256 * 1024):
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self) -> None:
        global PROCESS, STATE_PATH, STATE, LOG_HANDLE
        if not self.authorized():
            self.respond(403, {'error': 'Phiên làm việc không hợp lệ. Hãy mở lại EXE.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 42 * 1024 * 1024:
                raise ValueError('Dữ liệu quá lớn hoặc trống.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Dữ liệu không hợp lệ.')
            with LOCK:
                state = current_state()
                if self.path == '/api/folder':
                    os.startfile(str(ROOT / 'outputs'))
                elif self.path == '/api/cancel':
                    if PROCESS is not None:
                        subprocess.run(['taskkill', '/PID', str(PROCESS.pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        PROCESS.wait(timeout=10)
                        PROCESS = None
                        if LOG_HANDLE is not None:
                            LOG_HANDLE.close()
                            LOG_HANDLE = None
                    STATE = {'status': 'cancelled', 'message': 'Đã dừng. Bạn có thể chỉnh nội dung và tạo lại.', 'percent': 0}
                elif self.path == '/api/start':
                    if state['status'] == 'running':
                        self.respond(409, {'error': 'Đang tạo âm thanh, hãy chờ hoặc bấm Dừng.'})
                        return
                    content = data.get('text')
                    if not isinstance(content, str) or not content.strip() or len(content) > 30000:
                        raise ValueError('Nội dung phải từ 1 đến 30.000 ký tự.')
                    if data.get('consent') is not True:
                        raise ValueError('Cần xác nhận quyền sử dụng giọng mẫu.')
                    speed = data.get('speed', 0.96)
                    pause = data.get('pause', 0.3)
                    if not isinstance(speed, (int, float)) or not math.isfinite(speed) or not 0.75 <= speed <= 1.25:
                        raise ValueError('Tốc độ không hợp lệ.')
                    if not isinstance(pause, (int, float)) or not math.isfinite(pause) or not 0 <= pause <= 1.5:
                        raise ValueError('Khoảng nghỉ không hợp lệ.')
                    output_format = data.get('format')
                    if output_format not in ('mp3', 'wav'):
                        raise ValueError('Chỉ hỗ trợ MP3 và WAV.')
                    job_id = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3)
                    folder = ROOT / 'work' / job_id
                    folder.mkdir(parents=True)
                    reference = ROOT / 'voices' / 'MC-mau.wav'
                    uploaded = data.get('audio')
                    if uploaded is not None:
                        if not isinstance(uploaded, str):
                            raise ValueError('Giọng mẫu không hợp lệ.')
                        name = data.get('audioName')
                        suffix = Path(name).suffix.lower() if isinstance(name, str) else ''
                        if suffix not in ('.wav', '.mp3', '.m4a', '.flac', '.ogg'):
                            raise ValueError('Định dạng giọng mẫu không hỗ trợ.')
                        decoded = base64.b64decode(uploaded, validate=True)
                        if not 100 <= len(decoded) <= 30 * 1024 * 1024:
                            raise ValueError('Giọng mẫu trống hoặc lớn hơn 30 MB.')
                        reference = folder / ('reference' + suffix)
                        reference.write_bytes(decoded)
                    request = folder / 'request.json'
                    request.write_text(json.dumps({'text': content, 'speed': speed, 'pause': pause, 'format': output_format, 'reference': str(reference), 'output': f'Giong-Viet-{job_id}.{output_format}'}, ensure_ascii=False), encoding='utf-8')
                    STATE_PATH = folder / 'progress.json'
                    STATE = {'status': 'running', 'message': 'Đang khởi động bộ tạo giọng…', 'percent': 1}
                    LOG_HANDLE = (ROOT / 'logs' / f'{job_id}.log').open('w', encoding='utf-8')
                    environment = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
                    PROCESS = subprocess.Popen([str(ROOT / 'runtime' / 'python.exe'), str(ROOT / 'worker.py'), str(request)], cwd=ROOT, stdout=LOG_HANDLE, stderr=subprocess.STDOUT, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    self.send_error(404)
                    return
                self.respond(200, dict(STATE))
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            if self.path == '/api/start' and PROCESS is None:
                STATE = {'status': 'failed', 'message': str(error), 'percent': 0}
                if LOG_HANDLE is not None:
                    LOG_HANDLE.close()
                    LOG_HANDLE = None
            self.respond(400, {'error': str(error)})


def main() -> None:
    for directory in ('outputs', 'work', 'logs'):
        (ROOT / directory).mkdir(exist_ok=True)
    for dependency in ('web/index.html', 'worker.py', 'runtime/python.exe', 'bin/ffmpeg.exe', 'voices/MC-mau.wav'):
        if not (ROOT / dependency).is_file():
            raise FileNotFoundError(f'Thiếu {dependency}. Hãy giải nén và giữ nguyên toàn bộ thư mục portable.')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{server.server_port}/?token={TOKEN}'
    print('GIỌNG VIỆT STUDIO — Đang mở giao diện trong trình duyệt.', flush=True)
    print('Giữ cửa sổ này trong khi tạo giọng. Đóng cửa sổ để tắt ứng dụng.', flush=True)
    print('Âm thanh được lưu ở:', ROOT / 'outputs', flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        if PROCESS is not None and PROCESS.poll() is None:
            subprocess.run(['taskkill', '/PID', str(PROCESS.pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        server.server_close()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        details = traceback.format_exc()
        print(details, flush=True)
        try:
            (ROOT / 'LOI-KHOI-DONG.txt').write_text(details, encoding='utf-8')
        except OSError:
            pass
        input('Không mở được ứng dụng. Nhấn Enter để đóng…')
