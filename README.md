# Chat Global - Ready for Local & Render

Projeto pronto: chat global em tempo real com Flask + SocketIO + SQLite.

## Rodar localmente
1. Crie e ative venv:
   ```bash
   python -m venv venv
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   # Windows (cmd)
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Rode:
   ```bash
   python app.py
   ```
4. Abra http://localhost:5000
Usuários de teste: alice / password123  e  bob / password123

## Deploy no Render
- Conecte seu repositório no Render e use:
  - Build command: `pip install -r requirements.txt`
  - Start command: `gunicorn -k eventlet -w 1 app:app`
- Ou use o `Procfile` incluído.
