document.getElementById('btn-fetch').addEventListener('click', async () => {
    const urlInput = document.getElementById('video-url').value;
    const status = document.getElementById('status');
    const resultDiv = document.getElementById('result');
    const btnFetch = document.getElementById('btn-fetch');
    
    if (!urlInput) {
        alert("Pega un link primero");
        return;
    }

    status.textContent = "🔌 Conectando con el servidor local...";
    btnFetch.disabled = true;
    resultDiv.style.display = 'none';

    try {
        console.log("Iniciando búsqueda...");
        const res = await fetch(`/api/get-metadata?url=${encodeURIComponent(urlInput)}`);
        
        if (!res.ok) {
            status.textContent = "❌ El servidor respondió con un error.";
            btnFetch.disabled = false;
            return;
        }

        status.textContent = "📡 Extrayendo información de YouTube...";
        const data = await res.json();

        if (data.error) {
            status.innerHTML = `<span style="color:#ff6b6b">❌ Error de YouTube: ${data.error}</span>`;
            btnFetch.disabled = false;
            return;
        }

        document.getElementById('video-thumb').src = data.thumbnail;
        document.getElementById('video-title').textContent = data.title;
        resultDiv.style.display = 'block';
        status.textContent = "✅ ¡Video listo!";

        const btnDl = document.getElementById('btn-download');
        btnDl.onclick = async () => {
            btnDl.disabled = true;
            btnDl.textContent = "⏳ Preparando link de descarga...";
            
            try {
                const dlRes = await fetch(`/api/get-direct-url?video_id=${data.video_id}`);
                const dlData = await dlRes.json();
                
                if (dlData.url) {
                    status.textContent = "🚀 Descarga iniciada";
                    const a = document.createElement('a');
                    a.href = dlData.url;
                    a.download = data.title + ".mp4";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    btnDl.textContent = "¡Descarga iniciada!";
                } else {
                    status.textContent = "❌ Error al obtener el link.";
                }
            } catch (e) {
                status.textContent = "❌ Error de servidor.";
            }
            
            setTimeout(() => {
                btnDl.disabled = false;
                btnDl.innerHTML = '<i data-lucide="download"></i> Descargar MP4';
                lucide.createIcons();
            }, 3000);
        };

    } catch (e) {
        console.error("Fetch error:", e);
        status.innerHTML = `<span style="color:#ff6b6b">❌ ERROR: No se puede conectar al servidor.<br>Asegúrate de que 'INICIAR_LOCAL.bat' esté abierto.</span>`;
    }
    
    btnFetch.disabled = false;
});
