Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\Fastvideo.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.CurrentDirectory & "\INICIAR_LOCAL.bat"
oLink.WorkingDirectory = oWS.CurrentDirectory
oLink.Description = "Descarga videos de YouTube"
oLink.IconLocation = "shell32.dll, 160"
oLink.Save
WScript.Echo "✅ Acceso directo creado en el Escritorio."
