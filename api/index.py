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
    c.execute(f'SELECT * FROM users WHERE username = {PH}', ('admin',))
    if not fetchrow(c):
        admin_hash = generate_password_hash('admin')
        c.execute(f'INSERT INTO users (username, password_hash, role) VALUES ({PH}, {PH}, {PH})',
                  ('admin', admin_hash, 'admin'))
        logging.info("📝 Creado el usuario por defecto: username 'admin' | password 'admin'.")
    conn.commit()
    conn.close()

init_db()

def get_user_from_token(token):
    if not token: return None
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f'SELECT * FROM users WHERE token = {PH}', (token,))
    user = fetchrow(c)
    conn.close()
    return user


# --- ENDPOINTS MIDDLEWARE - PROTECCIÓN ---

def is_authorized(request_obj, required_role=None):
    # Soporta token en Authorization header o en querystring (para el <a> tag de descarga nativa)
    token = request_obj.headers.get('Authorization')
    if not token and request_obj.args.get('token'):
        token = request_obj.args.get('token')
        
    if token and token.startswith('Bearer '):
        token = token.split(' ')[1]
        
    user = get_user_from_token(token)
    if not user: return None
    if required_role and user['role'] != required_role: return None
    return user

# --- SERVIDOR DE ARCHIVOS ESTÁTICOS (FRONTEND) ---
from flask import send_from_directory

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

# --- RUTAS DE AUTENTICACIÓN Y ADMINISTRACIÓN ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Faltan credenciales"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f'SELECT * FROM users WHERE username = {PH}', (username,))
    user = fetchrow(c)
    if user and check_password_hash(user['password_hash'], password):
        token = secrets.token_hex(20)
        c.execute(f'UPDATE users SET token = {PH} WHERE id = {PH}', (token, user['id']))
        conn.commit()
        conn.close()
        return jsonify({"token": token, "username": user['username'], "role": user['role']})
        
    conn.close()
    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    admin_user = is_authorized(request, 'admin')
    if not admin_user: return jsonify({"error": "Acceso denegado"}), 403
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, role FROM users')
    users = fetchall(c)
    conn.close()
    return jsonify(users)

@app.route('/api/admin/users', methods=['POST'])
def create_user():
    admin_user = is_authorized(request, 'admin')
    if not admin_user: return jsonify({"error": "Acceso denegado"}), 403
        
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({"error": "Datos incompletos"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    try:
        pw_hash = generate_password_hash(password)
        c.execute(f'INSERT INTO users (username, password_hash, role) VALUES ({PH}, {PH}, {PH})',
                     (username, pw_hash, role))
        conn.commit()
    except Exception:
        conn.close()
        return jsonify({"error": "Ese nombre de usuario ya existe"}), 409
    conn.close()
    return jsonify({"success": True}), 201

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    admin_user = is_authorized(request, 'admin')
    if not admin_user: return jsonify({"error": "Acceso denegado"}), 403
        
    if admin_user['id'] == user_id:
        return jsonify({"error": "No puedes eliminarte a ti mismo"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f'DELETE FROM users WHERE id = {PH}', (user_id,))
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
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f'SELECT * FROM users WHERE id = {PH}', (user_id,))
    user = fetchrow(c)
    if not user:
        conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    try:
        if username:
            c.execute(f'UPDATE users SET username = {PH} WHERE id = {PH}', (username, user_id))
        if password:
            pw_hash = generate_password_hash(password)
            c.execute(f'UPDATE users SET password_hash = {PH} WHERE id = {PH}', (pw_hash, user_id))
            c.execute(f'UPDATE users SET token = NULL WHERE id = {PH}', (user_id,))
        if role:
            if user_id == admin_user['id'] and role != 'admin':
                return jsonify({"error": "No puedes revocar tus propios admin rights"}), 400
            c.execute(f'UPDATE users SET role = {PH} WHERE id = {PH}', (role, user_id))
        conn.commit()
    except Exception:
        conn.close()
        return jsonify({"error": "Usuario ya existe"}), 409
        
    conn.close()
    return jsonify({"success": True})

# --- ENDPOINTS DE DESCARGADOR ---

def get_yt_dlp_cmd():
    return [sys.executable, '-m', 'yt_dlp', '--no-playlist']

def clean_filename(title):
    import re
    # Remueve caracteres que no son válidos para nombres de archivo
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    return safe_title.strip()

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    if not is_authorized(request):
        return jsonify({"error": "Acceso denegado. Debes iniciar sesión."}), 401
        
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        import urllib.request as ureq, urllib.parse as uparse
        # Usamos la API oEmbed de YouTube (sin restricción de IP, 100% gratuita)
        oembed_url = f"https://www.youtube.com/oembed?url={uparse.quote(url)}&format=json"
        with ureq.urlopen(oembed_url, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        # La thumbnail de alta resolución se puede construir por el video_id
        video_id = ''
        for part in [url]:
            for sep in ['v=', 'youtu.be/', '/embed/']:
                if sep in part:
                    video_id = part.split(sep)[-1].split('&')[0].split('?')[0]
                    break
        
        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else data.get('thumbnail_url', '')
        
        return jsonify({
            "title": data.get("title", "YouTube Video"),
            "thumbnail": thumbnail,
            "video_id": video_id,
            "duration": 0
        })
    except Exception as e:
        logging.error(f"Error getting metadata via oEmbed: {e}")
        return jsonify({"error": "No se pudo obtener la información del video."}), 500

@app.route('/api/get-direct-url', methods=['GET'])
def get_direct_url():
    if not is_authorized(request):
        return jsonify({"error": "No autorizado"}), 401
    
    video_id = request.args.get('video_id')
    if not video_id:
        return jsonify({"error": "Falta ID de video"}), 400
        
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 1. Intentamos con Onedownloader (Muy estable para cloud IPs)
    try:
        import urllib.request as ureq
        # Endpoint de info de Onedownloader (Pública)
        api_url = f"https://api.onedownloader.com/get-info?url={video_url}"
        req = ureq.Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with ureq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == 'success' and data.get('formats'):
                # Buscamos el primer MP4 con audio
                for fmt in data['formats']:
                    if fmt.get('extension') == 'mp4' and fmt.get('url'):
                        return jsonify({"url": fmt['url']})
    except Exception as e:
        logging.error(f"Onedownloader falló: {e}")

    # 2. Fallback a Savetube
    try:
        api_url = f"https://api.savetube.me/info/{video_id}"
        req = ureq.Request(api_url, headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"})
        with ureq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == True and data.get('data'):
                formats = data['data'].get('video_formats', [])
                if formats:
                    return jsonify({"url": formats[0]['url']})
    except Exception as e:
        logging.error(f"Savetube falló: {e}")
        
    return jsonify({"error": "Servidores saturados temporalmente. Intenta de nuevo."}), 500

if __name__ == '__main__':
    app.run(port=5000)
