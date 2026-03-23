import subprocess
import json
import logging
import sys
import os
import yt_dlp
import urllib.request as ureq
import urllib.parse as uparse
from flask import Flask, request, Response, jsonify, send_from_directory
from flask_cors import CORS

# --- CONFIGURACIÓN APP (ULTRA-SIMPLE LOCAL) ---
app = Flask(__name__, static_folder='./', static_url_path='')
CORS(app)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    full_path = os.path.join(app.static_folder, path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return send_from_directory(app.static_folder, path)
    return jsonify({"error": "No encontrado"}), 404

@app.route('/api/get-metadata')
def get_metadata():
    video_url = request.args.get('url')
    if not video_url: return jsonify({"error": "Falta URL"}), 400
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
        # Extraer el mejor MP4 disponible
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True
        }
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
        time.sleep(2)
        print("🌍 Abriendo Fastvideo Local...")
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser).start()
    
    print("\n" + "="*40)
    print("🚀 Fastvideo LOCAL v1.0 (RESTAURADO)")
    print("Panel: http://127.0.0.1:5000")
    print("="*40 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
