import sys
import os
import logging
import threading
import time
import urllib.request as ureq

# Configurar logging inmediato a un archivo para ver errores de arranque
logging.basicConfig(
    filename='error_log.txt',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_and_print(msg):
    print(msg)
    logging.info(msg)

try:
    log_and_print("🔍 Verificando librerias...")
    from flask import Flask, request, Response, jsonify, send_from_directory
    from flask_cors import CORS
    import yt_dlp
    import webbrowser
except ImportError as e:
    err_msg = f"\n❌ ERROR: Falta una libreria: {str(e)}\nEjecuta: pip install flask flask-cors yt-dlp"
    log_and_print(err_msg)
    input("Presiona ENTER para salir...")
    sys.exit(1)

app = Flask(__name__, static_folder='./', static_url_path='')
CORS(app)

# Rutas simples
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    full_path = os.path.join(app.static_folder, path)
    if os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    return "No encontrado", 404

@app.route('/api/get-metadata')
def get_metadata():
    url = request.args.get('url')
    log_and_print(f"📥 Solicitud metadata para: {url}")
    try:
        # Configuración optimizada para evitar esperas largas (sin playlists)
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True, 
            'noplaylist': True,
            'skip_download': True,
            'socket_timeout': 10
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            log_and_print("🔍 Extrayendo info de YouTube...")
            info = ydl.extract_info(url, download=False)
            log_and_print(f"✅ Exito: {info.get('title')}")
            return jsonify({
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "video_id": info.get('id')
            })
    except Exception as e:
        log_and_print(f"❌ Error Metadata: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-direct-url')
def get_direct_url():
    video_id = request.args.get('video_id')
    url = f"https://www.youtube.com/watch?v={video_id}"
    log_and_print(f"📥 Solicitud descarga para ID: {video_id}")
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best', 
            'quiet': True, 
            'no_warnings': True, 
            'noplaylist': True,
            'socket_timeout': 15
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            log_and_print("🔗 Generando link directo...")
            info = ydl.extract_info(url, download=False)
            return jsonify({"url": info.get('url')})
    except Exception as e:
        log_and_print(f"❌ Error Descarga: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/proxy-download')
def proxy_download():
    video_url = request.args.get('url')
    filename = request.args.get('filename', 'video.mp4')
    if not video_url: return "No URL", 400
    
    try:
        req = ureq.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = ureq.urlopen(req)
        content_length = response.getheader('Content-Length')
        
        def generate():
            for chunk in iter(lambda: response.read(1024*64), b""):
                yield chunk
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'video/mp4'
        }
        if content_length: headers['Content-Length'] = content_length
        
        return Response(generate(), headers=headers)
    except Exception as e:
        log_and_print(f"❌ Error Proxy: {e}")
        return str(e), 500

def start_browser():
    time.sleep(2)
    url = "http://127.0.0.1:5000"
    log_and_print(f"🌍 Abriendo {url} en tu navegador...")
    webbrowser.open(url)

if __name__ == '__main__':
    threading.Thread(target=start_browser, daemon=True).start()
    log_and_print("\n🚀 Fastvideo LOCAL v5.2 Iniciado!")
    log_and_print("Si no se abre solo, ve a: http://127.0.0.1:5000")
    
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except Exception as e:
        log_and_print(f"❌ Error al iniciar servidor: {e}")
        input("Presiona ENTER para salir...")
