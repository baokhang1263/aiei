document.addEventListener("DOMContentLoaded", () => {
  const socket = io({
    transports: ["websocket", "polling"]
  });

  const messages = document.getElementById("messages");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("message-input");
  const roomButtons = document.querySelectorAll(".room-btn");

  let currentRoom = window.__INITIAL__?.defaultRoom || "general";
  const username = window.__INITIAL__?.username || "Guest";

  // Tham gia phòng mặc định
  socket.emit("join", { room: currentRoom, username });

  // Chuyển kênh chat
  roomButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const newRoom = btn.dataset.room;
      if (newRoom !== currentRoom) {
        socket.emit("leave", { room: currentRoom, username });
        currentRoom = newRoom;
        messages.innerHTML = "";
        socket.emit("join", { room: currentRoom, username });
      }
    });
  });

  // Nhận tin nhắn
  socket.on("message", (data) => {
    const item = document.createElement("div");
    item.classList.add("message");

    // Style riêng cho từng user
    if (data.username === "ai") {
      item.innerHTML = `<span class="msg-user ai">${data.username}:</span> ${data.msg} <span class="msg-time">· ${data.time}</span>`;
    } else if (data.username === "ei") {
      item.innerHTML = `<span class="msg-user ei">${data.username}:</span> ${data.msg} <span class="msg-time">· ${data.time}</span>`;
    } else {
      item.innerHTML = `<span class="msg-user">${data.username}:</span> ${data.msg} <span class="msg-time">· ${data.time}</span>`;
    }

    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  });

  // Nhận thông báo hệ thống (ai vào/ra)
  socket.on("status", (data) => {
    const item = document.createElement("div");
    item.classList.add("status");
    item.textContent = data.msg;
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  });

  // Gửi tin nhắn
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (input.value.trim() !== "") {
      socket.emit("message", { room: currentRoom, msg: input.value, username });
      input.value = "";
    }
  });
});
