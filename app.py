from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# --- Config ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# production cookie hardening (override via env if needed)
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'

ALLOW_SELF_REGISTER = os.environ.get('ALLOW_SELF_REGISTER', '0') in ('1', 'true', 'True')

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
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

def login_required():
    if not current_user():
        return redirect(url_for('login'))

# --- Routes ---
@app.route('/', methods=['GET'])
def index():
    if not current_user():
        return redirect(url_for('login'))
    rooms = ['general', 'random', 'tech']
    return render_template('index.html', rooms=rooms, username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            session['username'] = user.username
            return redirect(url_for('index'))
        return render_template('login.html', error='Sai thông tin đăng nhập hoặc tài khoản đã bị khóa')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Registration is disabled by default (pre-provision only)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if not ALLOW_SELF_REGISTER:
        abort(404)
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            return render_template('register.html', error='Điền đủ thông tin')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username đã tồn tại')
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/history/<room>')
def history(room):
    if not current_user():
        return {'error': 'unauthorized'}, 401
    msgs = Message.query.filter_by(room=room).order_by(Message.created_at.desc()).limit(100).all()
    return {'messages': [
        {'username': m.username, 'text': m.text, 'created_at': m.created_at.isoformat()}
        for m in reversed(msgs)
    ]}

# --- Socket.IO Events ---
@socketio.on('join')
def handle_join(data):
    room = data.get('room', 'general')
    username = session.get('username', None)
    if not username:
        return
    join_room(room)
    emit('system', {'text': f'{username} đã vào phòng {room}'}, to=room)

@socketio.on('leave')
def handle_leave(data):
    room = data.get('room', 'general')
    username = session.get('username', None)
    if not username:
        return
    leave_room(room)
    emit('system', {'text': f'{username} đã rời phòng {room}'}, to=room)

@socketio.on('message')
def handle_message(data):
    room = data.get('room', 'general')
    text = data.get('text', '').strip()
    username = session.get('username', None)
    if not username or not text:
        return
    msg = Message(room=room, username=username, text=text)
    db.session.add(msg)
    db.session.commit()
    emit('message', {'username': username, 'text': text, 'created_at': msg.created_at.isoformat()}, to=room)

# --- CLI Admin Commands ---
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Initialized the database.')

@app.cli.command('create-user')
def create_user_cmd():
    import getpass
    uname = input('Username: ').strip()
    if not uname:
        print('Username rỗng'); return
    if User.query.filter_by(username=uname).first():
        print('Đã tồn tại'); return
    pwd = getpass.getpass('Password: ')
    u = User(username=uname, is_active=True)
    u.set_password(pwd)
    db.session.add(u); db.session.commit()
    print('Tạo xong')

@app.cli.command('reset-password')
def reset_password_cmd():
    import getpass
    uname = input('Username: ').strip()
    u = User.query.filter_by(username=uname).first()
    if not u:
        print('Không tìm thấy user'); return
    pwd = getpass.getpass('New password: ')
    u.set_password(pwd); db.session.commit()
    print('Đổi mật khẩu xong')

@app.cli.command('deactivate-user')
def deactivate_user_cmd():
    uname = input('Username: ').strip()
    u = User.query.filter_by(username=uname).first()
    if not u:
        print('Không tìm thấy user'); return
    u.is_active = False; db.session.commit()
    print('Đã khóa tài khoản')

@app.cli.command('list-users')
def list_users_cmd():
    users = User.query.order_by(User.created_at.asc()).all()
    for u in users:
        status = 'active' if u.is_active else 'inactive'
        print(f'{u.username}  -  {status}  -  {u.created_at.isoformat()}')
# ==== ONE-TIME BOOTSTRAP ROUTE (xóa sau khi chạy xong) ====
import os
from flask import request

@app.route("/__init_users")
def __init_users():
    # bảo vệ bằng token để người lạ không gọi bừa
    token = request.args.get("token", "")
    expected = os.environ.get("BOOTSTRAP_TOKEN")
    if not expected or token != expected:
        return "forbidden", 403

    created = []

    def ensure_user(u, p):
        if not User.query.filter_by(username=u).first():
            user = User(username=u)
            user.set_password(p)
            db.session.add(user)
            created.append(u)

    # tạo 2 user bạn yêu cầu
    ensure_user("ei", "eiei")
    ensure_user("ai", "aiai")
    db.session.commit()

    if created:
        return f"created: {', '.join(created)}"
    return "no-op (users already exist)"
# ==== END BOOTSTRAP ROUTE ====
# ==== ONE-TIME PASSWORD RESET (delete after use) ====
from flask import request

@app.route("/__set_pw")
def __set_pw():
    token = request.args.get("token", "")
    expected = os.environ.get("BOOTSTRAP_TOKEN")
    if not expected or token != expected:
        return "forbidden", 403

    u = request.args.get("u", "").strip()
    p = request.args.get("p", "").strip()
    if not u or not p:
        return "missing u or p", 400

    user = User.query.filter_by(username=u).first()
    if not user:
        # nếu chưa có thì tạo mới
        user = User(username=u, is_active=True)
        db.session.add(user)

    user.is_active = True
    user.set_password(p)
    db.session.commit()
    return f"ok: set password for {u}"
# ==== END ONE-TIME PASSWORD RESET ====

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
