async function postJSON(url, data){ 
  const res = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  return res.json().then(j=>({ok:res.ok, status:res.status, body:j}));
}

document.addEventListener('DOMContentLoaded', ()=>{
  const path = location.pathname;
  if(path === '/' ){
    const btn = document.getElementById('btnLogin');
    btn.addEventListener('click', async ()=>{
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      const r = await postJSON('/api/login',{email,password});
      const msg = document.getElementById('msg');
      if(r.ok){
        localStorage.setItem('access_token', r.body.access_token);
        localStorage.setItem('refresh_token', r.body.refresh_token);
        localStorage.setItem('user', JSON.stringify(r.body.user));
        location.href = '/chat';
      } else {
        msg.textContent = r.body.msg || 'Erro';
      }
    });
  } else if(path === '/register'){
    const btn = document.getElementById('btnRegister');
    btn.addEventListener('click', async ()=>{
      const username = document.getElementById('username').value;
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      const r = await postJSON('/api/register',{username,email,password});
      const msg = document.getElementById('msg');
      if(r.ok){
        msg.textContent = 'Conta criada. Você pode entrar.';
        setTimeout(()=>location.href='/',1200);
      } else {
        msg.textContent = r.body.msg || (r.body.error || 'Erro');
      }
    });
  }
});
