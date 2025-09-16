import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# =====================
# App + DB config
# =====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL chưa được thiết lập!")

# Dùng psycopg v3
def to_psycopg3_url(url: str) -> str:
    if not url:
        return "sqlite:///chat.db"
    # postgres://...  -> postgresql+psycopg://...
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    # postgresql://... -> postgresql+psycopg://...
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

raw_url = os.environ.get("DATABASE_URL", "sqlite:///chat.db")
db_url = to_psycopg3_url(raw_url)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 5,
}
db = SQLAlchemy(app)

# =====================
# Models
# =====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50), default="general", index=True)
    username = db.Column(db.String(80))
    text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# =====================
# Routes
# =====================

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    rooms = ["general", "random"]
    return render_template("index.html", rooms=rooms, username=session.get("username"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
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
    msgs = (
        Message.query.filter_by(room=room)
        .order_by(Message.timestamp.asc())
        .all()
    )
    return [
        {"username": m.username, "text": m.text, "timestamp": m.timestamp.isoformat()}
        for m in msgs
    ]

# =====================
# Bootstrap routes
# =====================
@app.route("/__dbinfo")
def __dbinfo():
    token = request.args.get("token", "")
    expected = os.environ.get("BOOTSTRAP_TOKEN")
    if not expected or token != expected:
        return "forbidden", 403
    return jsonify({
        "dialect": db.engine.dialect.name,
        "driver": db.engine.dialect.driver,
        "url": str(db.engine.url).split("?")[0]
    })

@app.route("/__set_pw")
def __set_pw():
    token = request.args.get("token", "")
    expected = os.environ.get("BOOTSTRAP_TOKEN")
    if not expected or token != expected:
        return "forbidden", 403

    u = (request.args.get("u") or "").strip()
    p = (request.args.get("p") or "").strip()
    if not u or not p:
        return "missing u or p", 400

    user = User.query.filter_by(username=u).first()
    if not user:
        user = User(username=u, is_active=True)
        db.session.add(user)
    user.is_active = True
    user.set_password(p)
    db.session.commit()
    return f"ok: set password for {u}"

# =====================
# Error logging helper
# =====================
@app.errorhandler(Exception)
def _log_unhandled(e):
    import traceback, sys
    print("=== UNHANDLED FLASK ERROR ===", file=sys.stderr)
    traceback.print_exc()
    return "Internal Server Error", 500

# =====================
# Main
# =====================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
