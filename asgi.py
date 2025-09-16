# asgi.py  (UTF-8, không BOM)
import asyncio
import socketio
from datetime import datetime
from asgiref.wsgi import WsgiToAsgi

from app import app as flask_app   # import Flask app từ app.py

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=20,
    ping_timeout=60,
)

# Gắn Flask app vào ASGI wrapper
asgi_app = socketio.ASGIApp(sio, flask_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("asgi:asgi_app", host="0.0.0.0", port=5000)


# Bọc Flask (WSGI) vào ASGI và ghép với Socket.IO
flask_asgi = WsgiToAsgi(flask_app)
asgi_app = socketio.ASGIApp(sio, other_asgi_app=flask_asgi)

# ====== EVENTS ======

@sio.event
async def connect(sid, environ, auth):
    username = (auth or {}).get("username") or "Guest"
    await sio.save_session(sid, {"username": username})
    print(f"[connect] {sid} as {username}")

@sio.event
async def join(sid, data):
    room = (data or {}).get("room", "general")
    session = await sio.get_session(sid)
    username = session.get("username", "Guest")

    await sio.enter_room(sid, room)
    await sio.emit("system", {"text": f"{username} đã vào phòng {room}"}, room=room)
    print(f"[join] {username} -> {room}")

@sio.event
async def message(sid, data):
    room = (data or {}).get("room", "general")
    text = (data or {}).get("text", "").strip()
    if not text:
        return

    session = await sio.get_session(sid)
    username = session.get("username", "Guest")

    # Ghi DB trong thread để không block event loop
    def write_msg():
        with flask_app.app_context():
            m = Message(room=room, username=username, text=text)
            db.session.add(m)
            db.session.commit()
            return m.created_at

    created_at = await asyncio.to_thread(write_msg)

    await sio.emit(
        "message",
        {"username": username, "text": text, "created_at": created_at.isoformat()},
        room=room,
    )
    print(f"[msg] {username}@{room}: {text}")

@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    username = session.get("username", "Guest")
    print(f"[disconnect] {sid} ({username})")
