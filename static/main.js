// static/main.js
document.addEventListener("DOMContentLoaded", () => {
  const USER = (window.__INITIAL__ && window.__INITIAL__.username) || "Guest";
  const DEFAULT_ROOM = (window.__INITIAL__ && window.__INITIAL__.defaultRoom) || "general";

  // PHẢI có socket.io client trước file này
  if (typeof io !== "function") {
    console.error("Socket.IO client chưa load (io is not defined). Kiểm tra <script src='https://cdn.socket.io/4.7.5/socket.io.min.js'> trong base.html");
    return;
  }

  // Kết nối + gửi username qua auth
  const socket = io({
    path: "/socket.io/",
    transports: ["websocket", "polling"],
    auth: { username: USER }
  });

  const elMessages = document.getElementById("messages");
  const elForm = document.getElementById("chat-form");
  const elInput = document.getElementById("message-input");
  const roomBtns = document.querySelectorAll(".room-btn");

  let currentRoom = DEFAULT_ROOM;

  socket.on("connect", () => {
    console.log("[client] connected", socket.id, "as", USER);
    socket.emit("join", { room: currentRoom });
  });

  socket.on("disconnect", (reason) => {
    console.warn("[client] disconnected:", reason);
  });

  // Server phát event 'system' cho join/leave
  socket.on("system", (data) => {
    addSystemMessage(data?.text || "");
  });

  // Server phát event 'message' với {username, text, created_at}
  socket.on("message", (data) => {
    console.log("[client] on message:", data);
    const username = data?.username || "Guest";
    const text = data?.text ?? data?.msg ?? "";
    const createdAt = data?.created_at ?? data?.time ?? new Date().toISOString();
    addMessage(username, text, createdAt);
  });

  // Gửi tin
  elForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = (elInput.value || "").trim();
    if (!text) return;
    console.log("[client] emit message:", { room: currentRoom, text });
    socket.emit("message", { room: currentRoom, text });
    elInput.value = "";
    elInput.focus();
  });

  // Đổi phòng
  roomBtns.forEach((b) => {
    b.addEventListener("click", () => {
      const newRoom = b.dataset.room;
      if (!newRoom || newRoom === currentRoom) return;
      console.log("[client] change room:", currentRoom, "->", newRoom);
      socket.emit("leave", { room: currentRoom });
      currentRoom = newRoom;
      elMessages.innerHTML = "";
      socket.emit("join", { room: currentRoom });
    });
  });

  // ===== helpers =====
  function esc(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }
  function addMessage(username, text, created_at) {
    const d = document.createElement("div");
    const ts = new Date(created_at).toLocaleTimeString();
    let cls = "msg";
    if (username === "ai") cls += " ai";
    else if (username === "ei") cls += " ei";
    else cls += " other";
    d.className = cls;
    d.innerHTML = `<span class="author">${esc(username)}:</span> <span class="text">${esc(text)}</span><span class="time"> · ${ts}</span>`;
    elMessages.appendChild(d);
    elMessages.scrollTop = elMessages.scrollHeight;
  }
  function addSystemMessage(text) {
    const d = document.createElement("div");
    d.className = "system";
    d.textContent = text;
    elMessages.appendChild(d);
    elMessages.scrollTop = elMessages.scrollHeight;
  }
});
