import subprocess
import json
import logging
import sys
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Permite solicitudes desde el frontend servido en el puerto 8000
CORS(app)

logging.basicConfig(level=logging.INFO)

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_PATH = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
    # Validar si el admin base existe
    c.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not c.fetchone():
        admin_hash = generate_password_hash('admin')
        c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                  ('admin', admin_hash, 'admin'))
        logging.info("📝 Creado el usuario por defecto: username 'admin' | password 'admin'.")
    conn.commit()
    conn.close()

init_db()

def get_user_from_token(token):
    if not token: return None
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE token = ?', (token,)).fetchone()
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

# --- RUTAS DE AUTENTICACIÓN Y ADMINISTRACIÓN ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Faltan credenciales"}), 400
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user and check_password_hash(user['password_hash'], password):
        token = secrets.token_hex(20)
        conn.execute('UPDATE users SET token = ? WHERE id = ?', (token, user['id']))
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
    users = conn.execute('SELECT id, username, role FROM users').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

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
    try:
        pw_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                     (username, pw_hash, role))
        conn.commit()
    except sqlite3.IntegrityError:
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
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
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
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "Usuario no encontrado"}), 404
        
    try:
        if username:
            conn.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        if password:
            pw_hash = generate_password_hash(password)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (pw_hash, user_id))
            conn.execute('UPDATE users SET token = NULL WHERE id = ?', (user_id,))
        if role:
            if user_id == admin_user['id'] and role != 'admin':
                return jsonify({"error": "No puedes revocar tus propios admin rights"}), 400
            conn.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
        conn.commit()
    except sqlite3.IntegrityError:
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
        # Usa yt-dlp para obtener metadata en formato JSON
        cmd = get_yt_dlp_cmd() + ['-j', '--no-warnings', url]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8')
        data = json.loads(output)
        
        return jsonify({
            "title": data.get("title", "YouTube Video"),
            "thumbnail": data.get("thumbnail", ""),
            "duration": data.get("duration", 0)
        })
    except Exception as e:
        logging.error(f"Error getting metadata: {e}")
        return jsonify({"error": "No se pudo obtener la información del video."}), 500

@app.route('/api/download', methods=['GET'])
def download_video():
    if not is_authorized(request):
        return jsonify({"error": "Acceso denegado. Sessión inválida."}), 401
        
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
        
    # Obtenemos el título real para nombrar el archivo correctamente
    try:
        title_cmd = get_yt_dlp_cmd() + ['--get-title', url]
        title = subprocess.check_output(title_cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        filename = f"{clean_filename(title)}.mp4"
    except Exception as e:
        logging.error(f"Error getting title before download: {e}")
        filename = "Fastvideo_Download.mp4"
        
    # Stream the video directamente desde YouTube. 
    # 'best[ext=mp4]/best' descargará un MP4 unificado (video+audio) si existe, evitando el uso de ffmpeg.
    cmd = get_yt_dlp_cmd() + ['-f', 'best[ext=mp4]/best', '-o', '-', url]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'video/mp4'
    }
    
    # Generador para transmitir el contenido del video según se descarga
    def generate():
        try:
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                yield chunk
        except GeneratorExit:
            # Si el usuario cancela la descarga, detenemos el proceso
            logging.info("Descarga cancelada por el usuario.")
            process.terminate()
        except Exception as e:
            logging.error(f"Error transmitiendo stream: {e}")
            process.terminate()
        finally:
            process.wait()

    return Response(generate(), headers=headers)

if __name__ == '__main__':
    print("="*50)
    print("🚀 Iniciando el servidor Backend de Fastvideo en el puerto 5000...")
    print("⚠️ Asegúrate de mantener esta ventana abierta mientras usas la página.")
    print("="*50)
    app.run(port=5000, threaded=True)
