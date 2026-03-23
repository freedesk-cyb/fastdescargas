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

        // Mostrar resultado (Miniatura primero)
        videoThumb.src = data.thumbnail;
        document.getElementById('video-title').textContent = data.title;
        resultDiv.style.display = 'block';
        
        status.innerHTML = "🚀 <b>¡Video encontrado! Conectando reproductor...</b>";
        
        try {
            // Obtener link directo para reproducción y descarga
            const dlRes = await fetch(`/api/get-direct-url?video_id=${data.video_id}`);
            const dlData = await dlRes.json();
            
            if (dlData.url) {
                // ACTIVAR REPRODUCTOR
                videoThumb.style.display = 'none';
                videoPlayer.src = dlData.url;
                videoPlayer.style.display = 'block';
                videoPlayer.play().catch(e => console.log("Auto-play bloqueado por el navegador"));
                
                status.innerHTML = "✅ <b>¡Listo!</b> Puedes reproducir el video arriba o descargarlo.";
                
                // --- AUTO DESCARGA ---
                const a = document.createElement('a');
                a.href = dlData.url;
                a.download = data.title + ".mp4";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                status.innerHTML = "❌ No se pudo conectar el reproductor. Usa el botón de abajo.";
            }
        } catch (e) {
            status.innerHTML = "❌ Falló la conexión del video. Intenta de nuevo.";
        }

    } catch (e) {
        status.innerHTML = `<span style="color:#ff6b6b">❌ Error de conexión. Revisa el archivo .bat</span>`;
    }
    
    btnFetch.disabled = false;
});

// Botón manual por si falla la auto-descarga
document.getElementById('btn-download').addEventListener('click', async () => {
    const videoPlayer = document.getElementById('video-player');
    const title = document.getElementById('video-title').textContent;
    
    if (videoPlayer.src) {
        const a = document.createElement('a');
        a.href = videoPlayer.src;
        a.download = title + ".mp4";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } else {
        alert("Primero busca un video para descargar.");
    }
});
