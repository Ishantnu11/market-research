$pids = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($pids) {
    $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}
Start-Process -NoNewWindow -FilePath '.\venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--reload','--host','0.0.0.0','--port','8001'
