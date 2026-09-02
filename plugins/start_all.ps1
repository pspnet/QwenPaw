# ============================================================
# QwenPaw 插件服务启动脚本
# ============================================================

# --- 配置 ---
$env:OMATE_CONSOLE_URL          = "http://localhost:8080"
$env:OMATE_MEMORY_SYNC_INTERVAL = "10"
$env:UV_LINK_MODE               = "copy"

# JWT Token (必须是单行，不能换行)
$env:OMATE_USER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3JfYWJjMTIzZGVmNDU2IiwidXNlcm5hbWUiOiJhZG1pbiIsImFsaWFzIjoi566h55CG5ZGYIiwiY29kZSI6IkVNUDAwMSIsIm5pY2tuYW1lIjoiQWRtaW4gVXNlciIsImRlcGFydG1lbnQiOiLmioDmnK_pg6giLCJlbmFibGVkIjp0cnVlLCJyb2xlcyI6WyJhZG1pbiIsInVzZXIiXSwidHlwZSI6ImFjY2Vzc190b2tlbiIsImV4cCI6MjEwMzY2ODMxNiwiaWF0IjoxNzg4MzA4MzE2fQ.KVPsQF-QUpRKrj5h-t6ErtDPTw5RCPksacO_ro6LqzU"

# --- 路径配置 ---
$ProjectDir = "E:\workspace\liberty\QwenPaw"
$PythonPath = "D:\python\312\python.exe"

# --- 启动 ---
if (-not (Test-Path $ProjectDir)) {
    Write-Error "项目目录不存在: $ProjectDir"
    exit 1
}

Set-Location $ProjectDir
Write-Host "Starting QwenPaw on 0.0.0.0:8088 ..." -ForegroundColor Cyan
uv run --python $PythonPath qwenpaw app --host 0.0.0.0 --port 8088
