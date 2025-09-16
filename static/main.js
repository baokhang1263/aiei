// static/main.js

// Lấy username render từ Flask (đã được set trong index.html)
const CURRENT_USER =
  (window.__INITIAL__ && window.__INITIAL__.username)
    ? window.__INITIAL__.username
    : "Guest";

// Kết nối Socket.IO, gửi username qua auth
const socket = io({
  auth: { username: CURRENT_USER }
});

// Khi kết nối thành công → join vào phòng mặc định
socket.on("connect", () => {
  const room =
    (window.__INITIAL__ && window.__INITIAL__.defaultRoom)
      ? window.__INITIAL__.defaultRoom
      : "general";
  socket.emit("join", { room: room });
});

// Khi nhận tin nhắn từ server
socket.on("message", (data) => {
  addMessage(data.username, data.text, data.created_at);
});

// Khi nhận thông báo hệ thống (ai vào/ra phòng)
socket.on("system", (data) => {
  addSystemMessage(data.text);
});

// Gửi tin nhắn từ form
const form = document.getElementById("chat-form");
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("message");
  const text = (input.value || "").trim();
  if (!text) return;

  socket.emit("message", { room: "general", text: text });
  input.value = "";
});

// Hàm thêm tin nhắn vào khung chat
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function addMessage(username, text, created_at) {
  const messages = document.getElementById("messages");
  const div = document.createElement("div");

  const ts = created_at ? new Date(created_at).toLocaleTimeString() : new Date().toLocaleTimeString();

  // gắn class theo user để CSS tô màu
  let cls = "msg";
  if (username === "ai") cls += " ai";
  else if (username === "ei") cls += " ei";
  else cls += " other";

  div.className = cls;
  div.innerHTML =
    `<span class="author">${escapeHtml(username)}:</span> ` +
    `<span class="text">${escapeHtml(text)}</span>` +
    `<span class="time"> · ${ts}</span>`;

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}


// Hàm thêm thông báo hệ thống
function addSystemMessage(text) {
  const messages = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = "system";
  div.innerText = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}
