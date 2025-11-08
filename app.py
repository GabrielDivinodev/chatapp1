from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit
import sqlite3, os, datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'instance', 'database.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'replace-this-with-a-secure-key'
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )''')
    conn.commit()
    # create sample users if none
    c.execute('SELECT COUNT(*) as cnt FROM users')
    if c.fetchone()['cnt'] == 0:
        pw = bcrypt.generate_password_hash('password123').decode('utf-8')
        c.execute('INSERT INTO users (username,password,created_at) VALUES (?,?,?)',
                  ('alice', pw, datetime.datetime.utcnow().isoformat()))
        c.execute('INSERT INTO users (username,password,created_at) VALUES (?,?,?)',
                  ('bob', pw, datetime.datetime.utcnow().isoformat()))
        conn.commit()
    conn.close()

init_db()

# --- Helpers ---
@app.before_request
def load_user():
    g.user = None
    if 'user_id' in session:
        conn = get_db(); c = conn.cursor()
        c.execute('SELECT id,username FROM users WHERE id=?', (session['user_id'],))
        row = c.fetchone()
        conn.close()
        if row:
            g.user = {'id': row['id'], 'username': row['username']}

# --- Routes ---
@app.route('/')
def index():
    if g.user:
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    username = request.form.get('username','').strip()
    password = request.form.get('password','')
    if not username or not password:
        return render_template('register.html', error='Preencha todos os campos')
    conn = get_db(); c = conn.cursor()
    try:
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        c.execute('INSERT INTO users (username,password,created_at) VALUES (?,?,?)',
                  (username, hashed, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except sqlite3.IntegrityError:
        conn.close()
        return render_template('register.html', error='Nome de usuário já existe')

@app.route('/login', methods=['POST'])
def login():
    email_or_user = request.form.get('username','').strip()
    password = request.form.get('password','')
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT id,username,password FROM users WHERE username=?', (email_or_user,))
    row = c.fetchone()
    conn.close()
    if not row or not bcrypt.check_password_hash(row['password'], password):
        return render_template('login.html', error='Credenciais inválidas')
    session['user_id'] = row['id']
    return redirect(url_for('chat'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/chat')
def chat():
    if not g.user:
        return redirect(url_for('index'))
    # load last 100 messages
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT id,user_id,username,message,timestamp FROM messages ORDER BY id DESC LIMIT 100')
    rows = c.fetchall()
    conn.close()
    messages = [dict(r) for r in reversed(rows)]
    return render_template('chat.html', messages=messages, user=g.user)

@app.route('/api/messages', methods=['GET'])
def api_messages():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT id,user_id,username,message,timestamp FROM messages ORDER BY id DESC LIMIT 200')
    rows = c.fetchall(); conn.close()
    return jsonify([dict(r) for r in reversed(rows)])

# --- SocketIO events ---
@socketio.on('connect')
def on_connect():
    # nothing special on connect for global chat
    pass

@socketio.on('send_message')
def handle_send_message(data):
    text = data.get('message','').strip()
    if not text:
        return
    user_id = data.get('user_id')
    username = data.get('username','Anon')
    ts = datetime.datetime.utcnow().isoformat()
    conn = get_db(); c = conn.cursor()
    c.execute('INSERT INTO messages (user_id,username,message,timestamp) VALUES (?,?,?,?)',
              (user_id, username, text, ts))
    conn.commit()
    mid = c.lastrowid
    conn.close()
    payload = {'id': mid, 'user_id': user_id, 'username': username, 'message': text, 'timestamp': ts}
    emit('new_message', payload, broadcast=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
