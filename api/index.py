import subprocess
import json
import logging
import sys
import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

# --- CONFIGURACIÓN BASE DE DATOS (Portable para PostgreSQL y SQLite) ---
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    try:
        if db_url:
            import pg8000.dbapi
            import urllib.parse as uparse
            import ssl
            
            uparse.uses_netloc.append("postgres")
            url = uparse.urlparse(db_url)
            
            # Forzar SSL para Render/Neon/Heroku
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            conn = pg8000.dbapi.connect(
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port,
                database=url.path.lstrip('/'),
                ssl_context=ssl_context
            )
            return conn
        else:
            import sqlite3
            # Vercel no deja escribir en la raíz, pero sí en /tmp
            db_path = '/tmp/database.db' if os.environ.get('VERCEL') else 'database.db'
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        logging.error(f"Error en get_db_connection: {e}")
        raise e

def fetchrow(query, params=()):
    params = params if isinstance(params, (list, tuple)) else (params,)
    ph = '%s' if os.environ.get('DATABASE_URL') else '?'
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query.replace('?', ph), params)
        row = cursor.fetchone()
        if row and not hasattr(row, 'keys'): # Si es pg8000 (tupla)
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
        return dict(row) if row else None
    finally:
        if conn: conn.close()

def fetchall(query, params=()):
    params = params if isinstance(params, (list, tuple)) else (params,)
    ph = '%s' if os.environ.get('DATABASE_URL') else '?'
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query.replace('?', ph), params)
        rows = cursor.fetchall()
        # Convertir a lista de dicts
        if rows and len(rows) > 0 and not hasattr(rows[0], 'keys'):
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]
        return [dict(r) for r in rows]
    finally:
        if conn: conn.close()

def init_db():
    ph = '%s' if os.environ.get('DATABASE_URL') else '?'
    conn = get_db_connection()
    c = conn.cursor()
    if os.environ.get('DATABASE_URL'):
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                token TEXT
            )
        ''')
    else:
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
    
    # Verificar si existe el admin usando nuestro helper fetchrow
    admin = fetchrow('SELECT * FROM users WHERE username = ?', ('admin',))
    if not admin:
        admin_hash = generate_password_hash('admin')
        c.execute(f'INSERT INTO users (username, password_hash, role) VALUES ({ph}, {ph}, {ph})',
                  ('admin', admin_hash, 'admin'))
        conn.commit()
        logging.info("📝 Creado el usuario por defecto: admin/admin")
    conn.close()

try:
    init_db()
except Exception as e:
    logging.error(f"⚠️ Error al inicializar DB (en Vercel puede fallar en frio): {e}")

def get_user_from_token(token):
    if not token: return None
    return fetchrow('SELECT * FROM users WHERE token = ?', (token,))

# --- ENDPOINTS MIDDLEWARE - PROTECCIÓN ---

def is_authorized(request_obj, required_role=None):
    token = request_obj.headers.get('Authorization')
    if not token and request_obj.args.get('token'):
        token = request_obj.args.get('token')
        
    if token and token.startswith('Bearer '):
        token = token.split(' ')[1]
        
    user = get_user_from_token(token)
    if not user: return None
    if required_role and user['role'] != required_role: return None
    return user

# --- RUTAS DE AUTENTICACIÓN Y ADMINISTRACI@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Faltan credenciales"}), 400
        
    user = fetchrow('SELECT * FROM users WHERE username = ?', (username,))
    if user and check_password_hash(user['password_hash'], password):
        token = secrets.token_hex(20)
        ph = '%s' if os.environ.get('DATABASE_URL') else '?'
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(f'UPDATE users SET token = {ph} WHERE id = {ph}', (token, user['id']))
        conn.commit()
        conn.close()
        return jsonify({"token": token, "username": user['username'], "role": user['role']})
        
    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    if not is_authorized(request, 'admin'):
        return jsonify({"error": "Acceso denegado"}), 403
    users = fetchall('SELECT id, username, role FROM users')
    return jsonify(users)

@app.route('/api/admin/users', methods=['POST'])
def create_user():
    if not is_authorized(request, 'admin'):
        return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({"error": "Datos incompletos"}), 400
        
    ph = '%s' if os.environ.get('DATABASE_URL') else '?'
    try:
        conn = get_db_connection()
        c = conn.cursor()
        pw_hash = generate_password_hash(password)
        c.execute(f'INSERT INTO users (username, password_hash, role) VALUES ({ph}, {ph}, {ph})',
                     (username, pw_hash, role))
        conn.commit()
        conn.close()
        return jsonify({"success": True}), 201
    except Exception:
        return jsonify({"error": "Ese nombre de usuario ya existe o error BD"}), 409

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    admin_user = is_authorized(request, 'admin')
    if not admin_user: return jsonify({"error": "Acceso denegado"}), 403
        
    if admin_user['id'] == user_id:
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400
        
    ph = '%s' if os.environ.get('DATABASE_URL') else '?'
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f'DELETE FROM users WHERE id = {ph}', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})
    
@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    admin_user = is_authorized(request, 'admin')
    if not admin_user: return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    user = fetchrow('SELECT * FROM users WHERE id = ?', (user_id,))
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    ph = '%s' if os.environ.get('DATABASE_URL') else '?'
    try:
        conn = get_db_connection()
        c = conn.cursor()
        if username:
            c.execute(f'UPDATE users SET username = {ph} WHERE id = {ph}', (username, user_id))
        if password:
            pw_hash = generate_password_hash(password)
            c.execute(f'UPDATE users SET password_hash = {ph} WHERE id = {ph}', (pw_hash, user_id))
            c.execute(f'UPDATE users SET token = NULL WHERE id = {ph}', (user_id,))
        if role:
            if user_id == admin_user['id'] and role != 'admin':
                return jsonify({"error": "No puedes revocar tus propios admin rights"}), 400
            c.execute(f'UPDATE users SET role = {ph} WHERE id = {ph}', (role, user_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception:
        return jsonify({"error": "Error actualizando"}), 409

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    if not is_authorized(request):
        return jsonify({"error": "Acceso denegado"}), 401
    url = request.args.get('url')
    if not url: return jsonify({"error": "No URL"}), 400
    try:
        import urllib.request as ureq, urllib.parse as uparse
        oembed_url = f"https://www.youtube.com/oembed?url={uparse.quote(url)}&format=json"
        with ureq.urlopen(oembed_url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        video_id = ''
        for part in [url]:
            for sep in ['v=', 'youtu.be/', '/embed/']:
                if sep in part:
                    video_id = part.split(sep)[-1].split('&')[0].split('?')[0]
                    break
        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else data.get('thumbnail_url', '')
        return jsonify({"title": data.get("title"), "thumbnail": thumbnail, "video_id": video_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-direct-url', methods=['GET'])
def get_direct_url():
    if not is_authorized(request):
        return jsonify({"error": "No autorizado"}), 401
    video_id = request.args.get('video_id')
    if not video_id: return jsonify({"error": "Falta ID"}), 400
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        import urllib.request as ureq
        # 1. Onedownloader
        try:
            api_url = f"https://api.onedownloader.com/get-info?url={video_url}"
            req = ureq.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with ureq.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == 'success' and data.get('formats'):
                    for fmt in data['formats']:
                        if fmt.get('extension') == 'mp4' and fmt.get('url'): return jsonify({"url": fmt['url']})
        except: pass
        # 2. Savetube
        try:
            api_url = f"https://api.savetube.me/info/{video_id}"
            req = ureq.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with ureq.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('data'): return jsonify({"url": data['data']['video_formats'][0]['url']})
        except: pass
        return jsonify({"error": "Ocupado"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
