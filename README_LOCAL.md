# Fastvideo - Guía de Uso Local (Sin Bloqueos)

Si tienes problemas con Vercel ("Servidores ocupados" o "IP_BLOCKED"), la solución definitiva es correr el programa en tu propia computadora. Esto usa tu conexión de internet de casa, la cual **no está bloqueada** por YouTube.

## Requisitos
1.  **Python 3.x** instalado.
2.  Las librerías necesarias (se instalan una sola vez).

## Instrucciones Paso a Paso

1.  **Instalar dependencias**:
    Abre una terminal en la carpeta del proyecto y ejecuta:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Iniciar el programa**:
    Ejecuta el archivo `app.py`:
    ```bash
    python app.py
    ```

3.  **Acceder al panel**:
    Abre tu navegador y ve a:
    **http://127.0.0.1:5000**

4.  **¡Listo!**:
    Ahora puedes descargar cualquier video. El sistema usará tu IP residencial y funcionará siempre.

---

### ¿Cómo acceder desde fuera de casa? (Opcional)
Si quieres que otras personas entren a tu panel mientras tú lo tienes abierto en tu PC, te recomiendo usar **Ngrok** o **Cloudflare Tunnels**:
1. Descarga `ngrok`.
2. Ejecuta: `ngrok http 5000`.
3. Te dará una URL pública (ej: `https://abcd-123.ngrok.io`) que puedes compartir.
