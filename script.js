document.getElementById('btn-fetch').addEventListener('click', async () => {
    const urlInput = document.getElementById('video-url').value;
    const status = document.getElementById('status');
    const resultDiv = document.getElementById('result');
    const btnFetch = document.getElementById('btn-fetch');
    const videoThumb = document.getElementById('video-thumb');
    const videoPlayer = document.getElementById('video-player');
    
    if (!urlInput) {
        alert("Pega un link primero");
        return;
    }

    status.innerHTML = "🔍 <b>Buscando video...</b>";
    btnFetch.disabled = true;
    resultDiv.style.display = 'none';
    videoPlayer.style.display = 'none';
    videoThumb.style.display = 'block';

    try {
        const res = await fetch(`/api/get-metadata?url=${encodeURIComponent(urlInput)}`);
        if (!res.ok) throw new Error("Servidor no responde");
        
        const data = await res.json();
        if (data.error) {
            status.innerHTML = `<span style="color:#ff6b6b">❌ Error: ${data.error}</span>`;
            btnFetch.disabled = false;
            return;
        }

        // Mostrar resultado
        videoThumb.src = data.thumbnail;
        document.getElementById('video-title').textContent = data.title;
        resultDiv.style.display = 'block';
        
        status.innerHTML = "🚀 <b>¡Video encontrado! Conectando...</b>";
        
        try {
            const dlRes = await fetch(`/api/get-direct-url?video_id=${data.video_id}`);
            const dlData = await dlRes.json();
            
            if (dlData.url) {
                // ACTIVAR REPRODUCTOR
                videoThumb.style.display = 'none';
                videoPlayer.src = dlData.url;
                videoPlayer.style.display = 'block';
                videoPlayer.play().catch(e => console.log("Auto-play bloqueado"));
                
                status.innerHTML = "✅ <b>¡Listo!</b> Iniciando descarga en el panel...";
                
                // --- INLINE DOWNLOAD ---
                downloadInline(dlData.url, data.title + ".mp4");
            } else {
                status.innerHTML = "❌ No se pudo conectar el reproductor.";
            }
        } catch (e) {
            status.innerHTML = "❌ Falló la conexión del video.";
        }

    } catch (e) {
        status.innerHTML = "❌ Error de conexión con el servidor.";
    }
    
    btnFetch.disabled = false;
});

// FUNCIÓN DE DESCARGA INLINE CON PROGRESO
async function downloadInline(url, filename) {
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Iniciando descarga...';

    try {
        // Usar el proxy local para evitar problemas de CORS y navegación
        const response = await fetch(`/api/proxy-download?url=${encodeURIComponent(url)}&filename=${encodeURIComponent(filename)}`);
        if (!response.ok) throw new Error("Error en el servidor proxy");

        const reader = response.body.getReader();
        const contentLength = +response.headers.get('Content-Length');
        
        let receivedLength = 0;
        let chunks = []; 
        
        while(true) {
            const {done, value} = await reader.read();
            if (done) break;
            chunks.push(value);
            receivedLength += value.length;
            
            if (contentLength) {
                const percent = Math.round((receivedLength / contentLength) * 100);
                progressBar.style.width = percent + '%';
                progressText.textContent = `Descargando: ${percent}% (${(receivedLength / 1024 / 1024).toFixed(1)} MB)`;
            } else {
                progressText.textContent = `Descargando: ${(receivedLength / 1024 / 1024).toFixed(1)} MB...`;
            }
        }

        progressText.textContent = '✓ ¡Descarga completa! Guardando archivo...';
        const blob = new Blob(chunks, { type: 'video/mp4' });
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(downloadUrl);
        
        setTimeout(() => { progressContainer.style.display = 'none'; }, 5000);

    } catch (e) {
        console.error("Error downloadInline:", e);
        progressText.textContent = "❌ Error en descarga inline.";
        // Fallback simple a link directo si falla el proxy
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
    }
}

// Botón manual
document.getElementById('btn-download').addEventListener('click', async () => {
    const videoPlayer = document.getElementById('video-player');
    const title = document.getElementById('video-title').textContent;
    if (videoPlayer.src) {
        downloadInline(videoPlayer.src, title + ".mp4");
    } else {
        alert("Busca un video primero.");
    }
});
