import subprocess
import json
import logging
import sys
import os
import secrets
import yt_dlp
import urllib.request as ureq
import urllib.parse as uparse
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, Response, jsonify, send_from_directory
from flask_cors import CORS

# --- CONFIGURACIÓN APP (LOCAL) ---
app = Flask(__name__, static_folder='./', static_url_path='')
CORS(app)
logging.basicConfig(level=logging.INFO)

DB_PATH = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetchrow(query, params=()):
    params = params if isinstance(params, (list, tuple)) else (params,)
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"Error en fetchrow: {e}")
        return None
    finally:
        if conn: conn.close()

def fetchall(query, params=()):
    params = params if isinstance(params, (list, tuple)) else (params,)
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logging.error(f"Error en fetchall: {e}")
        return []
    finally:
        if conn: conn.close()

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            token TEXT
        )
    ''')
    conn.commit()
    
    admin = fetchrow('SELECT * FROM users WHERE username = ?', ('admin',))
    if not admin:
        admin_hash = generate_password_hash('admin')
        c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                  ('admin', admin_hash, 'admin'))
        conn.commit()
        logging.info("📝 Creado el usuario por defecto: admin/admin")
    conn.close()

def get_user_from_token(token):
    if not token: return None
    return fetchrow('SELECT * FROM users WHERE token = ?', (token,))

# --- RUTAS DE NAVEGACIÓN (STATIC) ---
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    full_path = os.path.join(app.static_folder, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return send_from_directory(app.static_folder, path)
    return jsonify({"error": "No encontrado"}), 404

# --- RUTAS DE API ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = fetchrow('SELECT * FROM users WHERE username = ?', (data.get('username'),))
    if user and check_password_hash(user['password_hash'], data.get('password')):
        token = secrets.token_hex(16)
        conn = get_db_connection()
        conn.execute('UPDATE users SET token = ? WHERE id = ?', (token, user['id']))
        conn.commit()
        conn.close()
        return jsonify({"token": token, "username": user['username'], "role": user['role']})
    return jsonify({"error": "Credenciales inválidas"}), 401

@app.route('/api/users', methods=['GET'])
def get_users():
    user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not user or user['role'] != 'admin': return jsonify({"error": "No autorizado"}), 403
    return jsonify(fetchall('SELECT id, username, role FROM users'))

@app.route('/api/users', methods=['POST'])
def add_user():
    current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not current_user or current_user['role'] != 'admin': return jsonify({"error": "No autorizado"}), 403
    data = request.json
    try:
        pwd_hash = generate_password_hash(data['password'])
        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                     (data['username'], pwd_hash, data.get('role', 'user')))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/users/<int:user_id>', methods=['PUT', 'DELETE'])
def manage_user(user_id):
    current_user = get_user_from_token(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not current_user or current_user['role'] != 'admin': return jsonify({"error": "No autorizado"}), 403
    conn = get_db_connection()
    if request.method == 'DELETE':
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    else: # PUT
        data = request.json
        if data.get('password'):
            pwd_hash = generate_password_hash(data['password'])
            conn.execute('UPDATE users SET username = ?, password_hash = ?, role = ? WHERE id = ?',
                         (data['username'], pwd_hash, data['role'], user_id))
        else:
            conn.execute('UPDATE users SET username = ?, role = ? WHERE id = ?',
                         (data['username'], data['role'], user_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})

@app.route('/api/get-metadata')
def get_metadata():
    video_url = request.args.get('url')
    if not video_url: return jsonify({"error": "Falta URL"}), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return jsonify({
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "video_id": info.get('id')
            })
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/get-direct-url')
def get_direct_url():
    video_id = request.args.get('video_id')
    video_url = request.args.get('url') or f"https://www.youtube.com/watch?v={video_id}"
    try:
        ydl_opts = {'format': 'best[ext=mp4]/best', 'quiet': True, 'no_warnings': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if info.get('url'): return jsonify({"url": info['url']})
        return jsonify({"error": "No se pudo extraer el link"}), 500
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import webbrowser
    import threading

    def open_browser():
        import time
        time.sleep(2) # Esperar a que el servidor arranque
        print("🌍 Abriendo el panel en tu navegador...")
        webbrowser.open("http://127.0.0.1:5000")

    with app.app_context():
        init_db()
    
    # Iniciar el hilo para abrir el navegador
    threading.Thread(target=open_browser).start()
    
    print("\n" + "="*40)
    print("🚀 Fastvideo LOCAL v4.1")
    print("Panel: http://127.0.0.1:5000")
    print("="*40 + "\n")
    
    # Intentar usar el puerto 5000 (el que el usuario prefiere)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Puerto 5000 ocupado, intentando 8080... ({e})")
        app.run(host='0.0.0.0', port=8080, debug=False)
