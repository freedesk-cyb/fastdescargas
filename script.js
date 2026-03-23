document.addEventListener('DOMContentLoaded', () => {
    // Auth Variables
    const API_URL = ''; // Rutas relativas para un solo servidor unificado
    let currentUser = {
        token: localStorage.getItem('fastvideo_token'),
        username: localStorage.getItem('fastvideo_username'),
        role: localStorage.getItem('fastvideo_role')
    };

    // UI Elements for Auth
    const loginView = document.getElementById('login-view');
    const appView = document.getElementById('app-view');
    const adminView = document.getElementById('admin-view');
    const navbar = document.getElementById('navbar');
    const userGreeting = document.getElementById('user-greeting');
    const btnAdminNav = document.getElementById('btn-admin-nav');
    const btnAppNav = document.getElementById('btn-app-nav');
    const btnLogout = document.getElementById('btn-logout');

    const btnLogin = document.getElementById('btn-login');
    const loginUserInp = document.getElementById('login-username');
    const loginPassInp = document.getElementById('login-password');
    const loginError = document.getElementById('login-error');

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

    // Router Logic
    function navigateTo(view) {
        loginView.style.display = 'none';
        appView.style.display = 'none';
        adminView.style.display = 'none';
        
        if (view === 'login') {
            navbar.style.display = 'none';
            loginView.style.display = 'flex';
        } else {
            navbar.style.display = 'flex';
            userGreeting.textContent = `Hola, ${currentUser.username}`;
            userGreeting.style.display = 'inline-block';
            
            btnAdminNav.style.display = (currentUser.role === 'admin' && view !== 'admin') ? 'inline-block' : 'none';
            btnAppNav.style.display = (view !== 'app') ? 'inline-block' : 'none';
            
            if (view === 'app') {
                appView.style.display = 'block';
                inputUrl.focus();
            }
            if (view === 'admin') {
                adminView.style.display = 'block';
                loadUsers();
            }
        }
    }

    function checkAuth() {
        if (currentUser.token) navigateTo('app');
        else navigateTo('login');
    }

    // Login Events
    btnLogin.addEventListener('click', async () => {
        const username = loginUserInp.value.trim();
        const password = loginPassInp.value;
        if (!username || !password) return;
        
        btnLogin.disabled = true;
        btnLogin.innerHTML = '<i data-lucide="loader" class="spin" style="width: 18px; margin-right: 8px;"></i> Ingresando...';
        lucide.createIcons();
        
        try {
            const res = await fetch(`${API_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('fastvideo_token', data.token);
                localStorage.setItem('fastvideo_username', data.username);
                localStorage.setItem('fastvideo_role', data.role);
                loginError.style.display = 'none';
                currentUser = data;
                navigateTo('app');
            } else {
                loginError.textContent = data.error;
                loginError.style.display = 'block';
            }
        } catch (e) {
            loginError.textContent = "Error de conexión con el backend (app.py apagado).";
            loginError.style.display = 'block';
        } finally {
            btnLogin.disabled = false;
            btnLogin.innerHTML = '<i data-lucide="log-in" style="width: 18px; margin-right: 8px;"></i> Ingresar';
            lucide.createIcons();
        }
    });

    btnLogout.addEventListener('click', () => {
        localStorage.clear();
        currentUser = { token: null, username: null, role: null };
        loginUserInp.value = '';
        loginPassInp.value = '';
        navigateTo('login');
    });

    btnAdminNav.addEventListener('click', () => navigateTo('admin'));
    btnAppNav.addEventListener('click', () => navigateTo('app'));

    checkAuth();

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
            // Intento 1: API de Backend Local (app.py) protegido con token
            const metadataResponse = await fetch(`${API_URL}/api/metadata?url=${encodeURIComponent(url)}`, {
                headers: { 'Authorization': `Bearer ${currentUser.token}` }
            });
            
            if (metadataResponse.status === 401 || metadataResponse.status === 403) {
                btnLogout.click(); // Sesión expirada
                return;
            }

            if (metadataResponse.ok) {
                const metadata = await metadataResponse.json();
                showInPageResultLocal(url, metadata, API_URL);
            } else {
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

        const directUrlEndpoint = `${backendUrl}/api/get-direct-url?url=${encodeURIComponent(originalUrl)}`;

        downloadOptions.innerHTML = `
            <button id="btn-dl-main" class="btn-primary" style="text-decoration:none; padding: 1rem 2rem; width: 100%; justify-content: center; font-size: 1.1rem; border-radius: 12px; display: flex; align-items: center; gap: 8px;">
                <i data-lucide="download" style="width:20px"></i> <span id="btn-dl-text">Descargar MP4</span>
            </button>
            <div id="dl-status" style="font-size: 0.85rem; color: var(--text-muted); text-align: center; margin-top: 10px; width: 100%;"></div>
        `;
        
        lucide.createIcons();
        
        document.getElementById('btn-dl-main').addEventListener('click', async () => {
            const btn = document.getElementById('btn-dl-main');
            const btnText = document.getElementById('btn-dl-text');
            const status = document.getElementById('dl-status');
            
            btn.disabled = true;
            btnText.textContent = 'Preparando descarga...';
            status.textContent = 'Obteniendo enlace directo desde el navegador (sin bloqueos de servidor)...';
            
            // Lista expandida de espejos (mirrors) de Cobalt v7 y v10
            const instances = [
                "https://cobalt.crushready.com",
                "https://cobalt.hyrax.dedyn.io",
                "https://cobalt-api.lre.pl",
                "https://api.cobalt.tools",
                "https://cobalt.vxtwitter.com"
            ];
            
            const payload = {
                url: originalUrl,
                videoQuality: "720"
            };
            
            let downloadUrl = null;
            let lastErrorMessage = "Todos los servidores de descarga están saturados.";
            
            for (const base of instances) {
                // Probamos ambas rutas comunes por cada servidor
                for (const path of ["/api/json", "/"]) {
                    const apiUrl = base + path;
                    try {
                        console.log(`Buscando video en: ${apiUrl}`);
                        const response = await fetch(apiUrl, {
                            method: 'POST',
                            mode: 'cors',
                            headers: {
                                'Accept': 'application/json',
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(payload)
                        });
                        
                        // Si el servidor responde pero da error de autenticación (JWT), saltamos al siguiente espejo
                        if (response.status === 401 || response.status === 403) {
                            console.warn(`${apiUrl} requiere autenticación, saltando...`);
                            continue;
                        }
                        
                        const data = await response.json();
                        
                        if (data && data.url) {
                            downloadUrl = data.url;
                            break;
                        } else if (data && data.status === 'error' && data.error && data.error.code === 'error.api.auth.jwt.missing') {
                            console.warn(`${apiUrl} pide JWT, saltando...`);
                            continue;
                        } else if (data && data.error) {
                            lastErrorMessage = data.error.code || "Error desconocido";
                        }
                    } catch (e) {
                        // Error de red o CORS, seguimos probando el siguiente espejo
                        continue;
                    }
                }
                if (downloadUrl) break;
            }
            
            if (downloadUrl) {
                status.textContent = '✅ ¡Descarga iniciándose! Revisa las descargas de tu navegador.';
                const a = document.createElement('a');
                a.href = downloadUrl;
                // Usamos el título del video que ya obtuvimos
                const safeTitle = (document.querySelector('.result-card h3')?.textContent || 'video').replace(/[\\/*?:"<>|]/g, "");
                a.download = `${safeTitle}.mp4`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } else {
                status.textContent = `❌ ${lastErrorMessage}. Por favor, prueba otro video o inténtalo más tarde.`;
            }
            
            setTimeout(() => {
                btn.disabled = false;
                btnText.textContent = 'Descargar MP4';
                lucide.createIcons();
            }, 5000);
        });
        
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

    // --- Admin Dashboard Logic ---
    const btnShowAddUser = document.getElementById('btn-show-add-user');
    const addUserForm = document.getElementById('add-user-form');
    const btnSaveUser = document.getElementById('btn-save-user');
    const btnCancelUser = document.getElementById('btn-cancel-user');
    const inUsername = document.getElementById('new-username');
    const inPassword = document.getElementById('new-password');
    const inRole = document.getElementById('new-role');
    const editUserId = document.getElementById('edit-user-id');

    btnShowAddUser.addEventListener('click', () => {
        addUserForm.style.display = 'block';
        editUserId.value = '';
        inUsername.value = '';
        inPassword.value = '';
        inRole.value = 'user';
        inUsername.focus();
    });

    btnCancelUser.addEventListener('click', () => {
        addUserForm.style.display = 'none';
    });

    btnSaveUser.addEventListener('click', async () => {
        const username = inUsername.value.trim();
        const password = inPassword.value;
        const role = inRole.value;
        const id = editUserId.value;

        if (!username || (!password && !id)) {
            showToast("Datos incompletos.");
            return;
        }

        const method = id ? 'PUT' : 'POST';
        const url = id ? `${API_URL}/api/admin/users/${id}` : `${API_URL}/api/admin/users`;
        const payload = { username, role };
        if (password) payload.password = password;

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${currentUser.token}`
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                showToast(id ? "Usuario actualizado." : "Usuario creado.");
                addUserForm.style.display = 'none';
                loadUsers();
            } else {
                showToast(data.error);
            }
        } catch (e) {
            showToast("Error de conexión.");
        }
    });

    async function loadUsers() {
        try {
            const res = await fetch(`${API_URL}/api/admin/users`, {
                headers: { 'Authorization': `Bearer ${currentUser.token}` }
            });
            if (res.status === 401 || res.status === 403) {
                btnLogout.click(); return;
            }
            const users = await res.json();
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = '';
            users.forEach(u => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
                tr.innerHTML = `
                    <td style="padding: 1rem 1.5rem;">${u.id}</td>
                    <td style="padding: 1rem 1.5rem; font-weight: bold;">${u.username}</td>
                    <td style="padding: 1rem 1.5rem;">
                        <span style="background: ${u.role==='admin'?'var(--primary)':'rgba(255,255,255,0.1)'}; padding: 3px 8px; border-radius: 4px; font-size: 0.8rem;">
                            ${u.role}
                        </span>
                    </td>
                    <td style="padding: 1rem 1.5rem; text-align: right;">
                        <button class="btn-edit" data-id="${u.id}" data-user="${u.username}" data-role="${u.role}" style="background:transparent; border:none; color:white; cursor:pointer; margin-right:15px;" title="Editar"><i data-lucide="edit-2" style="width:16px;"></i></button>
                        ${u.username !== currentUser.username ? `<button class="btn-del" data-id="${u.id}" style="background:transparent; border:none; color:#ff6b6b; cursor:pointer;" title="Eliminar"><i data-lucide="trash-2" style="width:16px;"></i></button>` : ''}
                    </td>
                `;
                tbody.appendChild(tr);
            });
            lucide.createIcons();
            
            document.querySelectorAll('.btn-edit').forEach(b => {
                b.addEventListener('click', (e) => {
                    const btn = e.currentTarget;
                    editUserId.value = btn.dataset.id;
                    inUsername.value = btn.dataset.user;
                    inRole.value = btn.dataset.role;
                    inPassword.value = '';
                    addUserForm.style.display = 'block';
                    inUsername.focus();
                });
            });

            document.querySelectorAll('.btn-del').forEach(b => {
                b.addEventListener('click', async (e) => {
                    if(!confirm("¿Seguro que deseas eliminar este usuario?")) return;
                    const id = e.currentTarget.dataset.id;
                    try {
                        const res = await fetch(`${API_URL}/api/admin/users/${id}`, {
                            method: 'DELETE',
                            headers: { 'Authorization': `Bearer ${currentUser.token}` }
                        });
                        if(res.ok) {
                            showToast("Usuario eliminado.");
                            loadUsers();
                        } else {
                            const data = await res.json();
                            showToast(data.error);
                        }
                    } catch(e) {
                        showToast("Error de red.");
                    }
                });
            });

        } catch(e) {
            showToast("Error cargando tabla de usuarios.");
        }
    }
});
