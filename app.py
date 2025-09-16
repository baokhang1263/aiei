# app.py — Flask app thuần cho HTTP routes, models, auth, history API
# (Realtime Socket.IO đã chuyển sang asgi.py)

from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# --- Flask Config ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cookie hardening (bật trong production)
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'

db = SQLAlchemy(app)
# Tự tạo bảng nếu chưa có (an toàn gọi nhiều lần)
with app.app_context():
    db.create_all()


# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(80), index=True, default="general")
    username = db.Column(db.String(120), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Helpers ---
def current_user():
    uname = session.get('username')
    if not uname:
        return None
    return User.query.filter_by(username=uname, is_active=True).first()

# --- Optional: cache headers cho static để tải nhanh hơn ---
@app.after_request
def add_cache_headers(resp):
    try:
        p = request.path or ""
        if p.startswith("/static/"):
            resp.headers["Cache-Control"] = "public, max-age=86400"
    except Exception:
        pass
    return resp

# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    if not current_user():
        return redirect(url_for("login"))
    rooms = ["general", "random", "tech"]
    # Truyền username xuống template để client JS gửi auth cho Socket.IO (asgi.py)
    return render_template("index.html", rooms=rooms, username=session.get("username"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            session["username"] = user.username
            return redirect(url_for("index"))
        return render_template("login.html", error="Sai thông tin đăng nhập hoặc tài khoản đã bị khóa")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/history/<room>")
def history(room):
    if not current_user():
        return {"error": "unauthorized"}, 401
    msgs = (
        Message.query.filter_by(room=room)
        .order_by(Message.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "messages": [
            {
                "username": m.username,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(msgs)
        ]
    }

# --- CLI Admin Commands (dùng khi có shell cục bộ/production gói có shell) ---
@app.cli.command("init-db")
def init_db():
    """Khởi tạo database (tạo bảng)."""
    db.create_all()
    print("Initialized the database.")

@app.cli.command("create-user")
def create_user_cmd():
    """Tạo user mới (nhập từ console)."""
    import getpass
    uname = input("Username: ").strip()
    if not uname:
        print("Username rỗng"); return
    if User.query.filter_by(username=uname).first():
        print("Đã tồn tại"); return
    pwd = getpass.getpass("Password: ")
    u = User(username=uname, is_active=True)
    u.set_password(pwd)
    db.session.add(u); db.session.commit()
    print("Tạo xong")

@app.cli.command("reset-password")
def reset_password_cmd():
    """Đặt lại mật khẩu user."""
    import getpass
    uname = input("Username: ").strip()
    u = User.query.filter_by(username=uname).first()
    if not u:
        print("Không tìm thấy user"); return
    pwd = getpass.getpass("New password: ")
    u.set_password(pwd); db.session.commit()
    print("Đổi mật khẩu xong")

@app.cli.command("deactivate-user")
def deactivate_user_cmd():
    """Khóa tài khoản user."""
    uname = input("Username: ").strip()
    u = User.query.filter_by(username=uname).first()
    if not u:
        print("Không tìm thấy user"); return
    u.is_active = False; db.session.commit()
    print("Đã khóa tài khoản")

@app.cli.command("list-users")
def list_users_cmd():
    """Liệt kê user và trạng thái."""
    users = User.query.order_by(User.created_at.asc()).all()
    for u in users:
        status = "active" if u.is_active else "inactive"
        print(f"{u.username}  -  {status}  -  {u.created_at.isoformat()}")

# Lưu ý: KHÔNG cần if __name__ == "__main__" trên Render (chạy bằng Uvicorn qua asgi.py)
