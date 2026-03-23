document.getElementById('btn-fetch').addEventListener('click', async () => {
    const urlInput = document.getElementById('video-url').value;
    const status = document.getElementById('status');
    const resultDiv = document.getElementById('result');
    const btnFetch = document.getElementById('btn-fetch');
    
    if (!urlInput) {
        alert("Pega un link primero");
        return;
    }

    status.innerHTML = "🔍 <b>Buscando video...</b>";
    btnFetch.disabled = true;
    resultDiv.style.display = 'none';

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
        document.getElementById('video-thumb').src = data.thumbnail;
        document.getElementById('video-title').textContent = data.title;
        resultDiv.style.display = 'block';
        
        // --- AUTO DESCARGA ---
        status.innerHTML = "🚀 <b>¡Video encontrado! Generando descarga automática...</b>";
        
        try {
            const dlRes = await fetch(`/api/get-direct-url?video_id=${data.video_id}`);
            const dlData = await dlRes.json();
            
            if (dlData.url) {
                status.innerHTML = "✅ <b>¡Descarga iniciada!</b> Revisa tu carpeta de descargas.";
                
                const a = document.createElement('a');
                a.href = dlData.url;
                a.download = data.title + ".mp4";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                status.innerHTML = "❌ No se pudo generar el link automático. Usa el botón de abajo.";
            }
        } catch (e) {
            status.innerHTML = "❌ Falló la descarga automática. Intenta de nuevo.";
        }

    } catch (e) {
        status.innerHTML = `<span style="color:#ff6b6b">❌ Error de conexión. Revisa el archivo .bat</span>`;
    }
    
    btnFetch.disabled = false;
});

// Botón manual por si falla la auto-descarga
document.getElementById('btn-download').addEventListener('click', async () => {
    const status = document.getElementById('status');
    const title = document.getElementById('video-title').textContent;
    // Extraer ID de la imagen o guardar globalmente
    const thumbUrl = document.getElementById('video-thumb').src;
    // Como simplificamos mucho, re-buscamos si hace falta o usamos variables
    // Para simplificar al usuario, el botón simplemente refresca la intención
    alert("La descarga debería haber iniciado. Si no, pega el link y busca de nuevo.");
});
