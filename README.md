# Internal Chat (Pre-Provisioned Accounts Only)

Web chat qua Internet, **không cho đăng ký công khai** — chỉ đăng nhập bằng tài khoản đã tạo sẵn.

## Tính năng
- Realtime chat Socket.IO
- Kênh: #general / #random / #tech (tùy biến)
- Lưu 100 tin gần nhất/room
- Tài khoản chỉ do admin tạo (CLI)

## Chạy local
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

set FLASK_APP=app.py   # macOS/Linux: export FLASK_APP=app.py
flask init-db
flask create-user      # tạo user đầu tiên
set SECRET_KEY=chuoi-that-dai  # export trên macOS/Linux
python app.py
# http://localhost:5000
```

## Deploy Render.com (khuyến nghị)
- Build: `pip install -r requirements.txt`
- Start: `gunicorn -k eventlet -w 1 app:app`
- Env:
  - `SECRET_KEY`=chuỗi ngẫu nhiên dài
  - `DATABASE_URL`=URL PostgreSQL (Render cung cấp)  _vd: postgres://..._
  - `SESSION_COOKIE_SECURE`=`True` (bật HTTPS)
  - `SESSION_COOKIE_SAMESITE`=`Lax`
  - `ALLOW_SELF_REGISTER`=`0`  (mặc định đã tắt)
- Tạo user lần đầu: vào **Shell** của Render → chạy `flask init-db` rồi `flask create-user`

## Gắn tên miền & HTTPS
- Trỏ CNAME về Render → bật **Force HTTPS**.
- Tuỳ chọn đặt reverse proxy (Nginx/Caddy) nếu cần tuỳ chỉnh sâu.

## Scale & Đa instance
- Khi scale >1 instance, cấu hình **message queue** cho Socket.IO (Redis):
  - Cài thêm `redis` server & `pip install redis`
  - Tạo `socketio = SocketIO(app, message_queue='redis://...')`

## Lệnh quản trị
- `flask create-user` — tạo tài khoản
- `flask reset-password` — đổi mật khẩu
- `flask deactivate-user` — khóa tài khoản
- `flask list-users` — liệt kê tài khoản

## Bảo mật đề xuất
- Bắt buộc HTTPS; đặt `SECRET_KEY` dài.
- Đổi `rooms` theo phòng ban trong `index()`.
- Sao lưu DB/ dùng PostgreSQL cho sản xuất.
