# Chat Global - UI Improved (Flask + SocketIO + SQLite)

Features:
- Messages aligned right (self) and left (others)
- Responsive UI for mobile and desktop
- Real-time updates via SocketIO (no page refresh required)
- Secure password hashing with bcrypt
- Ready for Render (Procfile + gunicorn + eventlet)

## Quick start (local)
1. Create and activate venv:
   ```bash
   python -m venv venv
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   # Windows cmd
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
2. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python app.py
   ```
4. Open http://localhost:5000 and test with alice / password123

## Deploy on Render
- Build: `pip install -r requirements.txt`
- Start: `gunicorn -k eventlet -w 1 app:app`
