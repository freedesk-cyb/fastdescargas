from api.index import app
import os

if __name__ == '__main__':
    print("🚀 Iniciando Fastvideo LOCAL...")
    print("Accede a http://127.0.0.1:5000 para descargar videos sin bloqueos.")
    # Usar el puerto 5000 por defecto de Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
