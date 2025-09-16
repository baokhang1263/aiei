document.addEventListener("DOMContentLoaded", () => {
  const CURRENT_USER = (window.__INITIAL__ && window.__INITIAL__.username) || "Guest";
  const DEFAULT_ROOM = (window.__INITIAL__ && window.__INITIAL__.defaultRoom) || "general";

  // Gửi username qua auth để server lưu trong phiên socket
 const socket = io({
  path: "/socket.io/",
  transports: ["websocket", "polling"],
  auth: { username: (window.__INITIAL__?.username) || "Guest" }
});


  const messages = document.getElementById("messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");
  const roomButtons = document.querySelectorAll(".room-btn");

  let currentRoom = DEFAULT_ROOM;

  socket.on("connect", () => {
    socket.emit("join", { room: currentRoom }); // KHÔNG gửi username ở đây nữa
  });

  // --- NHẬN TIN NHẮN (chuẩn: username, text, created_at) ---
  socket.on("message", (data) => {
    // Hỗ trợ luôn trường hợp cũ (msg/time) nếu còn rơi rớt
    const username = data.username || "Guest";
    const text = data.text ?? data.msg ?? "";
    const createdAt = data.created_at ?? data.time ?? new Date().toISOString();
    addMessage(username, text, createdAt);
  });

  // --- THÔNG BÁO HỆ THỐNG ---
  socket.on("system", (data) => addSystemMessage(data.text || ""));

  // --- GỬI TIN: chuẩn {room, text} ---
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = (input.value || "").trim();
    if (!text) return;
    socket.emit("message", { room: currentRoom, text }); // <-- text (không phải msg)
    input.value = "";
  });

  // --- CHUYỂN PHÒNG ---
  roomButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const newRoom = btn.dataset.room;
      if (newRoom && newRoom !== currentRoom) {
        socket.emit("leave", { room: currentRoom });
        currentRoom = newRoom;
        messages.innerHTML = "";
        socket.emit("join", { room: currentRoom });
      }
    });
  });

  // ===== helpers =====
  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }
  function addMessage(username, text, created_at) {
    const div = document.createElement("div");
    const ts = new Date(created_at).toLocaleTimeString();
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
  function addSystemMessage(text) {
    const div = document.createElement("div");
    div.className = "system";
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }
});
