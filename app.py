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

# --- CONFIGURACIÓN BASE DE DATOS (SQLite local / PostgreSQL en producción) ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import pg8000.native
    import pg8000.dbapi
    from urllib.parse import urlparse
    PH = '%s'  # Placeholder para PostgreSQL

    _parsed = urlparse(DATABASE_URL)
    _PG = dict(
        host=_parsed.hostname,
        port=_parsed.port or 5432,
        database=_parsed.path.lstrip('/'),
        user=_parsed.username,
        password=_parsed.password,
        ssl_context=True
    )

    def get_db_connection():
        conn = pg8000.dbapi.connect(**_PG)
        conn.autocommit = False
        return conn
    def fetchrow(cursor):
        row = cursor.fetchone()
        if row is None: return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    def fetchall(cursor):
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, r)) for r in rows]
    logging.info("🐘 Usando PostgreSQL/pg8000 (producción)")
else:
    import sqlite3
    PH = '?'  # Placeholder para SQLite
    DB_PATH = 'database.db'
    def get_db_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    def fetchrow(cursor):
        row = cursor.fetchone()
        return dict(row) if row else None
    def fetchall(cursor):
        return [dict(r) for r in cursor.fetchall()]
    logging.info("🗄️ Usando SQLite (local)")

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    if DATABASE_URL:
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
            "duration": 0
        })
    except Exception as e:
        logging.error(f"Error getting metadata via oEmbed: {e}")
        return jsonify({"error": "No se pudo obtener la información del video."}), 500

@app.route('/api/get-direct-url', methods=['GET'])
def get_direct_url():
    if not is_authorized(request):
        return jsonify({"error": "Acceso denegado."}), 401
        
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
        
    try:
        import urllib.request as ureq
        import urllib.parse as uparse
        import urllib.error
        
        # Limpiamos la URL para remover parámetros de playlist (&list=...) 
        # que pueden dar error en Cobalt al intentar procesarlos como video único.
        clean_url = url
        if 'youtube.com/watch' in url:
            parsed_url = uparse.urlparse(url)
            qs = uparse.parse_qs(parsed_url.query)
            if 'v' in qs:
                clean_url = f"https://www.youtube.com/watch?v={qs['v'][0]}"
        elif 'youtu.be/' in url:
            clean_url = url.split('?')[0]
            
        logging.info(f"🚀 Solicitando Cobalt para: {clean_url}")
        
        # Usamos Cobalt.tools API — diseñada para esto, no bloqueada por YouTube
        cobalt_payload = json.dumps({
            "url": clean_url,
            "downloadMode": "auto",
            "videoQuality": "720",
            "filenameStyle": "classic"
        }).encode('utf-8')
        
        cobalt_req = ureq.Request(
            "https://api.cobalt.tools/",
            data=cobalt_payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )
        
        try:
            with ureq.urlopen(cobalt_req, timeout=30) as resp:
                cobalt_data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logging.error(f"Cobalt HTTP Error {e.code}: {error_body}")
            return jsonify({"error": f"API de descarga falló (Error {e.code}): {error_body}"}), 500
        
        logging.info(f"Cobalt response status: {cobalt_data.get('status')}")
        
        download_url = None
        if cobalt_data.get('status') in ('redirect', 'tunnel', 'stream'):
            download_url = cobalt_data.get('url')
        elif cobalt_data.get('status') == 'error':
            error_text = cobalt_data.get('error', {}).get('code', 'desconocido')
            return jsonify({"error": f"Error del servidor de descarga: {error_text}"}), 500
        
        if not download_url:
            return jsonify({"error": "No se recibió una URL válida del servidor de descarga."}), 500
        
        # Extraer título del video usando oEmbed
        title = "Fastvideo_Download"
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={uparse.quote(clean_url)}&format=json"
            with ureq.urlopen(oembed_url, timeout=10) as r:
                oembed = json.loads(r.read().decode('utf-8'))
                title = clean_filename(oembed.get('title', title))
        except:
            pass
        
        return jsonify({"url": download_url, "filename": f"{title}.mp4"})
        
    except Exception as e:
        logging.error(f"Error crítico con API de descarga: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("="*50)
    print("🚀 Iniciando el servidor Backend de Fastvideo en el puerto 5000...")
    app.run(port=5000, threaded=True)
