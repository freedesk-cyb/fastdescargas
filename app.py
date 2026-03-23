from api.index import app
import os

if __name__ == '__main__':
    print("🚀 Iniciando Fastvideo LOCAL...")
    print("Accede a http://127.0.0.1:8080 para descargar videos sin bloqueos.")
    # Cambiamos al puerto 8080 por si el 5000 está ocupado
    app.run(host='0.0.0.0', port=8080, debug=True)
