import os
import asyncio
import socketio
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Flask app
flask_app = Flask(__name__)

# Config database (Render sẽ truyền DATABASE_URL)
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

flask_app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///chat.db"
flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(flask_app)

# Model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with flask_app.app_context():
    db.create_all()

# Socket.IO
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)
asgi_app = socketio.ASGIApp(sio, flask_app)


# ------------------ Socket.IO events ------------------

@sio.event
async def connect(sid, environ, auth):
    username = (auth or {}).get("username", "Guest")
    await sio.save_session(sid, {"username": username})
    print(f"[connect] {username} ({sid}) connected")


@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    username = session.get("username", "Guest")
    print(f"[disconnect] {username} ({sid}) disconnected")


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

    # Save message vào DB
    def write_msg():
        with flask_app.app_context():
            m = Message(room=room, username=username, text=text)
            db.session.add(m)
            db.session.commit()
            return m.created_at

    created_at = await asyncio.to_thread(write_msg)

    # Phát tin nhắn lại cho room
    payload = {
        "username": username,
        "text": text,
        "created_at": created_at.isoformat()
    }
    print(f"[msg] {payload}")  # log để debug
    await sio.emit("message", payload, room=room)
