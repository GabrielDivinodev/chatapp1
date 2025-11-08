let socket = null;
let currentChat = null;
const token = localStorage.getItem('access_token');
if(!token){
  // redirect to login
  if(location.pathname !== '/'){ location.href = '/'; }
}

async function apiGET(path){
  const res = await fetch(path, {headers:{'Authorization':'Bearer '+token}});
  if(res.status === 401) { alert('Sessão expirada. Faça login.'); localStorage.clear(); location.href='/'; }
  return res.json();
}

function formatTime(iso){ try{ const d=new Date(iso); return d.toLocaleString(); }catch(e){return iso} }

function addContactDiv(u){
  const div = document.createElement('div');
  div.className = 'contact';
  div.dataset.id = u.id;
  div.innerHTML = `<div><strong>${u.username}</strong><div style="font-size:12px;color:#777">${u.email}</div></div>`;
  div.addEventListener('click', ()=>{ openChat(u); });
  document.getElementById('contacts').appendChild(div);
}

async function openChat(u){
  currentChat = u;
  document.getElementById('chatHeader').textContent = u.username;
  document.getElementById('messages').innerHTML = 'Carregando...';
  const msgs = await apiGET('/api/messages/'+u.id);
  const cont = document.getElementById('messages'); cont.innerHTML='';
  msgs.forEach(m=>{
    const el = document.createElement('div');
    el.className = 'message ' + (m.sender_id === JSON.parse(localStorage.getItem('user')).id ? 'me':'other');
    el.innerHTML = `<div>${m.message}</div><div style="font-size:11px;color:#666">${formatTime(m.timestamp)}</div>`;
    cont.appendChild(el);
  });
  cont.scrollTop = cont.scrollHeight;
}

async function loadContacts(){
  const users = await apiGET('/api/users');
  document.getElementById('contacts').innerHTML='';
  users.forEach(addContactDiv);
}

function setupSocket(){
  socket = io({transports:['websocket']});
  socket.on('connect', ()=>{
    console.log('socket connected');
    socket.emit('join', {token: token});
  });
  socket.on('joined', (d)=>{ console.log('joined', d); });
  socket.on('new_message', (m)=>{
    // if message belongs to currentChat or current user, update UI
    const myId = JSON.parse(localStorage.getItem('user')).id;
    if((currentChat && (m.sender_id==currentChat.id || m.receiver_id==currentChat.id)) || m.sender_id==myId || m.receiver_id==myId){
      // if current chat open, append
      if(currentChat && (m.sender_id==currentChat.id || m.receiver_id==currentChat.id)){
        const cont = document.getElementById('messages');
        const el = document.createElement('div');
        el.className = 'message ' + (m.sender_id === myId ? 'me':'other');
        el.innerHTML = `<div>${m.message}</div><div style="font-size:11px;color:#666">${formatTime(m.timestamp)}</div>`;
        cont.appendChild(el);
        cont.scrollTop = cont.scrollHeight;
      }
      // optional: mark contact or refresh list
    }
  });
  socket.on('error', (e)=>{ console.log('socket error', e); });
}

document.addEventListener('DOMContentLoaded', async ()=>{
  // ensure token exists, load user and contacts
  const user = JSON.parse(localStorage.getItem('user')||'null');
  if(!user){ location.href='/'; return; }
  document.getElementById('logoutBtn').addEventListener('click', ()=>{ localStorage.clear(); location.href='/'; });
  document.getElementById('sendBtn').addEventListener('click', sendMessage);
  document.getElementById('inputMessage').addEventListener('keydown', (e)=>{ if(e.key==='Enter') sendMessage(); });
  await loadContacts();
  setupSocket();
});

function sendMessage(){
  const text = document.getElementById('inputMessage').value.trim();
  if(!text || !currentChat) return;
  socket.emit('private_message', {token: token, to: currentChat.id, message: text});
  document.getElementById('inputMessage').value='';
}
