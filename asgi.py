# asgi.py — Socket.IO (asyncio) + Flask (WSGI) chạy trên Uvicorn (Python 3.13)
import asyncio
import socketio
from asgiref.wsgi import WsgiToAsgi
from datetime import datetime

# ⚠️ Đổi tên khi import để KHÔNG đè lên biến asgi_app bên dưới
from app import app as flask_app, db, Message

# Tạo Async Socket.IO server (ASGI)
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=20,
    ping_timeout=60,
    logger=False,
    engineio_logger=False,
)

# Bọc Flask (WSGI) thành ASGI
flask_asgi = WsgiToAsgi(flask_app)

# ✅ Xuất ASGI app với tên KHÁC (không phải "app" để tránh nhầm)
asgi_app = socketio.ASGIApp(sio, other_asgi_app=flask_asgi)

# ===== Socket.IO events =====
@sio.event
async def connect(sid, environ, auth):
    username = (auth or {}).get("username") or "Guest"
    sio.save_session(sid, {"username": username})

@sio.event
async def join(sid, data):
    room = (data or {}).get("room", "general")
    session = await sio.get_session(sid)
    username = session.get("username", "Guest")
    await sio.enter_room(sid, room)
    await sio.emit("system", {"text": f"{username} đã vào phòng {room}"}, room=room)

@sio.event
async def leave(sid, data):
    room = (data or {}).get("room", "general")
    session = await sio.get_session(sid)
    username = session.get("username", "Guest")
    await sio.leave_room(sid, room)
    await sio.emit("system", {"text": f"{username} đã rời phòng {room}"}, room=room)

@sio.event
async def message(sid, data):
    room = (data or {}).get("room", "general")
    text = (data or {}).get("text", "").strip()
    if not text:
        return
    session = await sio.get_session(sid)
    username = session.get("username", "Guest")

    # ✅ Ghi DB cần app_context từ Flask app GỐC
    def write_msg():
        with flask_app.app_context():
            m = Message(room=room, username=username, text=text, created_at=datetime.utcnow())
            db.session.add(m)
            db.session.commit()
            return m.created_at

    created_at = await asyncio.to_thread(write_msg)
    await sio.emit(
        "message",
        {"username": username, "text": text, "created_at": created_at.isoformat()},
        room=room
    )

@sio.event
async def disconnect(sid):
    pass
