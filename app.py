from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, decode_token
)
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, emit
import sqlite3, os, datetime, json

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'replace-this-with-a-secure-random-key'
app.config['JWT_SECRET_KEY'] = 'replace-this-with-a-different-secure-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # seconds
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# --- Database helpers ---
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
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
                )''')
    conn.commit()
    # create sample users if no users exist
    c.execute('SELECT COUNT(*) as cnt FROM users')
    if c.fetchone()['cnt'] == 0:
        pw = bcrypt.generate_password_hash('password123').decode('utf-8')
        c.execute('INSERT INTO users (username,email,password,created_at) VALUES (?,?,?,?)',
                  ('alice','alice@example.com',pw,datetime.datetime.utcnow().isoformat()))
        c.execute('INSERT INTO users (username,email,password,created_at) VALUES (?,?,?,?)',
                  ('bob','bob@example.com',pw,datetime.datetime.utcnow().isoformat()))
        conn.commit()
    conn.close()

init_db()

# --- Routes / API ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    username = data.get('username','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    if not username or not email or not password:
        return jsonify({'msg':'missing fields'}), 400
    conn = get_db(); c = conn.cursor()
    try:
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        c.execute('INSERT INTO users (username,email,password,created_at) VALUES (?,?,?,?)',
                  (username,email,hashed,datetime.datetime.utcnow().isoformat()))
        conn.commit()
        uid = c.lastrowid
        conn.close()
        return jsonify({'msg':'created','user_id':uid}), 201
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({'msg':'user exists','error':str(e)}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email=?', (email,))
    row = c.fetchone()
    conn.close()
    if not row: 
        return jsonify({'msg':'invalid credentials'}), 401
    if not bcrypt.check_password_hash(row['password'], password):
        return jsonify({'msg':'invalid credentials'}), 401
    user = {'id': row['id'], 'username': row['username'], 'email': row['email']}
    access = create_access_token(identity=user['id'])
    refresh = create_refresh_token(identity=user['id'])
    return jsonify({'access_token':access, 'refresh_token':refresh, 'user':user})

@app.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    identity = get_jwt_identity()
    access = create_access_token(identity=identity)
    return jsonify({'access_token': access})

@app.route('/api/user', methods=['GET'])
@jwt_required()
def api_user():
    uid = get_jwt_identity()
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT id,username,email,created_at FROM users WHERE id=?', (uid,))
    row = c.fetchone()
    conn.close()
    if not row: return jsonify({'msg':'not found'}), 404
    return jsonify(dict(row))

@app.route('/api/users', methods=['GET'])
@jwt_required()
def api_users():
    uid = get_jwt_identity()
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT id,username,email FROM users WHERE id != ?', (uid,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/messages/<int:other_id>', methods=['GET'])
@jwt_required()
def api_messages(other_id):
    uid = get_jwt_identity()
    conn = get_db(); c = conn.cursor()
    c.execute('''SELECT * FROM messages WHERE 
                 (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                 ORDER BY id ASC''', (uid, other_id, other_id, uid))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify(rows)

# Serve static files (optional explicit route)
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# --- SocketIO events ---
connected_users = {}  # socket sid -> user_id mapping

@socketio.on('join')
def handle_join(data):
    token = data.get('token')
    if not token:
        emit('error', {'msg':'no token'})
        return
    try:
        decoded = decode_token(token)
        uid = decoded.get('sub')
        # join a room named after the user id
        join_room(str(uid))
        connected_users[request.sid] = uid
        emit('joined', {'user_id': uid})
    except Exception as e:
        emit('error', {'msg':'invalid token', 'error': str(e)})

@socketio.on('private_message')
def handle_private_message(data):
    # data: {token, to, message}
    token = data.get('token'); to = data.get('to'); message = data.get('message','').strip()
    if not token or not to or not message:
        emit('error', {'msg':'missing fields'})
        return
    try:
        decoded = decode_token(token)
        sender_id = decoded.get('sub')
    except Exception as e:
        emit('error', {'msg':'invalid token'}); return
    ts = datetime.datetime.utcnow().isoformat()
    conn = get_db(); c = conn.cursor()
    c.execute('INSERT INTO messages (sender_id,receiver_id,message,timestamp) VALUES (?,?,?,?)',
              (sender_id, to, message, ts))
    conn.commit()
    mid = c.lastrowid
    conn.close()
    payload = {'id': mid, 'sender_id': sender_id, 'receiver_id': to, 'message': message, 'timestamp': ts}
    # send to receiver room and sender room
    emit('new_message', payload, room=str(to))
    emit('new_message', payload, room=str(sender_id))

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
