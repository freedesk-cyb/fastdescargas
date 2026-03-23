document.getElementById('btn-fetch').addEventListener('click', async () => {
    const urlInput = document.getElementById('video-url').value;
    const status = document.getElementById('status');
    const resultDiv = document.getElementById('result');
    
    if (!urlInput) {
        alert("Pega un link primero");
        return;
    }

    status.textContent = "Buscando información...";
    resultDiv.style.display = 'none';

    try {
        const res = await fetch(`/api/get-metadata?url=${encodeURIComponent(urlInput)}`);
        const data = await res.json();

        if (data.error) {
            status.textContent = "Error: " + data.error;
            return;
        }

        document.getElementById('video-thumb').src = data.thumbnail;
        document.getElementById('video-title').textContent = data.title;
        resultDiv.style.display = 'block';
        status.textContent = "¡Video encontrado!";

        // Configurar botón de descarga
        const btnDl = document.getElementById('btn-download');
        btnDl.onclick = async () => {
            btnDl.disabled = true;
            btnDl.textContent = "Preparando descarga...";
            
            try {
                const dlRes = await fetch(`/api/get-direct-url?video_id=${data.video_id}`);
                const dlData = await dlRes.json();
                
                if (dlData.url) {
                    const a = document.createElement('a');
                    a.href = dlData.url;
                    a.download = data.title + ".mp4";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    btnDl.textContent = "¡Descarga iniciada!";
                } else {
                    alert("No se pudo obtener el link de descarga.");
                }
            } catch (e) {
                alert("Error al conectar con el servidor.");
            }
            
            setTimeout(() => {
                btnDl.disabled = false;
                btnDl.innerHTML = '<i data-lucide="download"></i> Descargar MP4';
                lucide.createIcons();
            }, 3000);
        };

    } catch (e) {
        status.textContent = "Error de conexión con el servidor local.";
    }
});
