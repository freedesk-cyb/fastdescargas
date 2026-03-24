import sys
import os
import logging
import threading
import time
import subprocess
import urllib.request as ureq

# Soporte para PyInstaller y Vercel (Ruta de archivos temporales)
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # En Vercel, el directorio raíz suele ser el correcto
    return os.path.join(os.path.abspath("."), relative_path)

# Configurar logging
logging.basicConfig(
    filename='error_log.txt',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_and_print(msg):
    print(msg)
    logging.info(msg)

try:
    from flask import Flask, request, Response, jsonify, send_from_directory
    from flask_cors import CORS
    import yt_dlp
except ImportError as e:
    log_and_print(f"❌ Error librerias: {e}")
    # En Vercel las dependencias están en requirements.txt
    pass

static_folder = get_resource_path('.')
app = Flask(__name__, static_folder=static_folder, template_folder=static_folder)
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/get-metadata')
def get_metadata():
    url = request.args.get('url')
    log_and_print(f"📥 Metadata para: {url}")
    try:
        ydl_opts = {'quiet': True, 'noplaylist': True, 'skip_download': True, 'socket_timeout': 10}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
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
    log_and_print(f"📥 Descarga para: {video_id}")
    try:
        ydl_opts = {'format': 'best[ext=mp4]/best', 'quiet': True, 'noplaylist': True, 'socket_timeout': 15}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({"url": info.get('url')})
    except Exception as e:
        log_and_print(f"❌ Error URL: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/proxy-download')
def proxy_download():
    video_url = request.args.get('url')
    filename = request.args.get('filename', 'video.mp4')
    try:
        req = ureq.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = ureq.urlopen(req, timeout=30)
        content_length = response.getheader('Content-Length')
        def generate():
            for chunk in iter(lambda: response.read(1024*64), b""):
                yield chunk
        headers = {'Content-Disposition': f'attachment; filename="{filename}"', 'Content-Type': 'video/mp4'}
        if content_length: headers['Content-Length'] = content_length
        return Response(generate(), headers=headers)
    except Exception as e:
        return str(e), 500

def find_chrome():
    paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in paths:
        if os.path.exists(path): return path
    return None

def start_ui():
    time.sleep(2)
    url = "http://127.0.0.1:5000"
    chrome_path = find_chrome()
    if chrome_path:
        subprocess.Popen([chrome_path, f"--app={url}"])
    else:
        import webbrowser
        webbrowser.open(url)

if __name__ == '__main__':
    # Lanzar UI solo si no estamos en Vercel
    if not os.environ.get('VERCEL'):
        threading.Thread(target=start_ui, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
