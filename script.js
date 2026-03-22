document.addEventListener('DOMContentLoaded', () => {
    const btnFetch = document.getElementById('btn-fetch');
    const inputUrl = document.getElementById('video-url');
    const resultArea = document.getElementById('result-area');
    const loader = document.getElementById('loader');
    const btnText = document.getElementById('btn-text');
    const downloadIcon = document.getElementById('download-icon');
    const inputWrapper = document.querySelector('.input-wrapper');
    const toast = document.getElementById('toast');
    
    const videoTitle = document.getElementById('video-title');
    const videoThumb = document.getElementById('video-thumb');
    const videoPlaceholderIcon = document.getElementById('video-placeholder-icon');
    const downloadOptions = document.querySelector('.download-options');

    const ytRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;

    inputUrl.focus();

    btnFetch.addEventListener('click', async () => {
        const url = inputUrl.value.trim();

        if (!url) {
            showToast('Por favor, ingresa un link de YouTube.');
            return;
        }

        if (!ytRegex.test(url)) {
            showToast('El enlace no parece ser de YouTube. Verifica el formato.');
            return;
        }

        startLoading();

        try {
            // Intento 1: API de Backend Local (app.py)
            const backendUrl = 'http://127.0.0.1:5000';
            const metadataResponse = await fetch(`${backendUrl}/api/metadata?url=${encodeURIComponent(url)}`);
            
            if (metadataResponse.ok) {
                const metadata = await metadataResponse.json();
                showInPageResultLocal(url, metadata, backendUrl);
            } else {
                // El server local falló (probablemente no está corriendo)
                throw new Error('Servidor local apagado o error de metadata');
            }

        } catch (error) {
            console.error('Download System Error:', error);
            showToast('El servidor local no está activo. Mostrando alternativa externa.');
            showFallback(url);
        } finally {
            stopLoading();
        }
    });

    // Nueva función robusta para resultado usando App.py
    function showInPageResultLocal(originalUrl, metadata, backendUrl) {
        videoTitle.textContent = metadata.title || "¡Video Listo para Descargar!";
        if (metadata.thumbnail) {
            videoThumb.src = metadata.thumbnail;
            videoThumb.style.display = 'block';
            videoPlaceholderIcon.style.display = 'none';
        }

        const downloadUrl = `${backendUrl}/api/download?url=${encodeURIComponent(originalUrl)}`;

        downloadOptions.innerHTML = `
            <a href="${downloadUrl}" class="btn-primary" style="text-decoration:none; padding: 1rem 2rem; width: 100%; justify-content: center; font-size: 1.1rem; border: none; cursor: pointer; background: var(--primary); color: white; border-radius: 12px; display: flex; align-items: center; gap: 8px; transition: all 0.3s;">
                <i data-lucide="download" style="width:20px"></i> Descargar Nativamente (MP4)
            </a>
            <div style="font-size: 0.85rem; color: var(--text-muted); text-align: center; margin-top: 10px; width: 100%;">
                La descarga será procesada por tu backend local sin pestañas nuevas.
            </div>
        `;
        
        lucide.createIcons();
        resultArea.style.display = 'block';
        resultArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

        // ... (Trigger functionality is now replaced by direct <a> download which is native)

    function showFallback(url) {
        const videoId = extractVideoId(url);
        videoTitle.textContent = "Herramienta de Carga Alternativa";
        if (videoId) {
            videoThumb.src = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
            videoThumb.style.display = 'block';
            videoPlaceholderIcon.style.display = 'none';
        }

        // Si fallan las APIs, intentamos descargar forzando la redirección en la MISMA pestaña (target="_self")
        // Ocultamente a través de un iframe si el proxy de cobalts tools UI lo soporta.
        // Pero como cobalt.tools UI requiere interaccion, abrimos en la misma pestaña.
        const fallbackUrl = `https://cobalt.tools/?u=${encodeURIComponent(url)}`;

        downloadOptions.innerHTML = `
            <div style="margin-bottom:1rem; font-size: 0.95rem; color: var(--text-muted); line-height: 1.4;">
                Los servidores directos están saturados. Haz clic abajo para ir al servidor de respaldo y descargar.
            </div>
            <a href="${fallbackUrl}" target="_self" class="btn-primary" style="text-decoration:none; padding: 1rem 2rem; width: 100%; justify-content: center; display: flex; border-radius: 12px; align-items: center; gap: 8px;">
                <i data-lucide="zap" style="width:18px"></i> Ir al Servidor de Respaldo
            </a>
        `;
        
        lucide.createIcons();
        resultArea.style.display = 'block';
        resultArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function startLoading() {
        btnFetch.disabled = true;
        btnText.style.display = 'none';
        downloadIcon.style.display = 'none';
        loader.style.display = 'block';
        inputWrapper.classList.add('loading');
        resultArea.style.display = 'none';
    }

    function stopLoading() {
        btnFetch.disabled = false;
        btnText.style.display = 'inline';
        downloadIcon.style.display = 'inline-block';
        loader.style.display = 'none';
        inputWrapper.classList.remove('loading');
    }

    function showToast(msg) {
        toast.textContent = msg;
        toast.style.display = 'block';
        setTimeout(() => toast.style.display = 'none', 3000);
    }

    function extractVideoId(url) {
        const regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/;
        const match = url.match(regExp);
        return (match && match[7].length == 11) ? match[7] : false;
    }
});
