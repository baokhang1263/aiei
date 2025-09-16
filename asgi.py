# asgi.py
import asyncio
import socketio
from datetime import datetime
from asgiref.wsgi import WsgiToAsgi

from app import app as flask_app, db, Message

# Khởi tạo server Socket.IO (ASGI mode)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=20,
    ping_timeout=60,
)

# Bao bọc Flask app để chạy chung với Socket.IO
flask_asgi = WsgiToAsgi(flask_app)
asgi_app = socketio.ASGIApp(sio, other_asgi_app=flask_asgi)

# Khi client kết nối: lấy username từ auth
@sio.event
async def connect(sid, environ, auth):
    username = (auth or {}).get("username") or "Guest"
    await sio.save_session(sid, {"username": username})
    print(f"[connect] {sid} as {username}")

# Khi client join vào room
@sio.event
async def j
