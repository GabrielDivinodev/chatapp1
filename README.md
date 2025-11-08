# Chat Global - Eventlet-ready (Flask + SocketIO + SQLite)

### Features
- Login & register using bcrypt (secure hashing)
- Global real-time chat using Flask-SocketIO with eventlet
- SQLite database auto-initialized (includes alice/bob users)
- Procfile and requirements for Render deployment

### Run locally
1. Create venv and activate
   ```bash
   python -m venv venv
   # Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   # Windows (cmd)
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```
2. Install deps
   ```bash
   pip install -r requirements.txt
   ```
3. Run
   ```bash
   python app.py
   ```
4. Open http://localhost:5000
Users: alice / password123  and  bob / password123

### Deploy on Render
- Build: `pip install -r requirements.txt`
- Start: `gunicorn -k eventlet -w 1 app:app`
