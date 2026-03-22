import subprocess
import json
import logging
import sys
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Permite solicitudes desde el frontend servido en el puerto 8000
CORS(app)

logging.basicConfig(level=logging.INFO)

def get_yt_dlp_cmd():
    return [sys.executable, '-m', 'yt_dlp']

def clean_filename(title):
    import re
    # Remueve caracteres que no son válidos para nombres de archivo
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    return safe_title.strip()

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
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
