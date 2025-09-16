(function(){
  const socket = io();
  let currentRoom = (window.__INITIAL__ && window.__INITIAL__.defaultRoom) || 'general';
  const messagesEl = document.getElementById('messages');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('message-input');
  const roomButtons = document.querySelectorAll('.room-btn');

  function appendSystem(text){
    const div = document.createElement('div');
    div.className = 'msg system';
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  function appendMessage(username, text, time){
    const div = document.createElement('div');
    div.className = 'msg';
    const who = document.createElement('strong');
    who.textContent = username + ': ';
    const content = document.createElement('span');
    content.textContent = text;
    const meta = document.createElement('span');
    meta.className = 'meta';
    meta.textContent = time ? '  ·  ' + new Date(time).toLocaleTimeString() : '';
    div.appendChild(who); div.appendChild(content); div.appendChild(meta);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  function fetchHistory(room){
    fetch('/history/' + room).then(r => r.json()).then(data => {
      messagesEl.innerHTML = '';
      (data.messages || []).forEach(m => appendMessage(m.username, m.text, m.created_at));
    });
  }
  function join(room){
    currentRoom && socket.emit('leave', {room: currentRoom});
    currentRoom = room; appendSystem('Đã chuyển sang #' + room);
    fetchHistory(room); socket.emit('join', {room});
  }
  socket.on('connect', function(){ join(currentRoom); });
  socket.on('system', function(payload){ appendSystem(payload.text); });
  socket.on('message', function(payload){ appendMessage(payload.username, payload.text, payload.created_at); });
  form.addEventListener('submit', function(e){
    e.preventDefault();
    const text = (input.value || '').trim();
    if (!text) return;
    socket.emit('message', {room: currentRoom, text});
    input.value = '';
  });
  roomButtons.forEach(btn => btn.addEventListener('click', () => join(btn.dataset.room)));
})();
