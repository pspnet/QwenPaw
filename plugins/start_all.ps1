# a-console 远程服务地址
$env:OMATE_CONSOLE_URL = "http://localhost:8080"
$env:OMATE_USER_CODE = "Y014030"
$env:OMATE_USER_NAME = "于奥成"

# 通用 Token (JWT)
$env:OMATE_CONSOLE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiJhZG1pbiIsImFwcF9pZCI6InF3ZW5wYXciLCJhZ2VudF9pZCI6IiIsInJvbGVzIjpbImFkbWluIl0sInNjb3BlcyI6WyJhZG1pbjpyZWFkIiwiYWRtaW46d3JpdGUiXSwic3ViIjoiYWRtaW4iLCJleHAiOjE4MTkyNzYwMDUsImlhdCI6MTc4Nzc0MDAwNX0.L6m-4FhmY5udXZTNFIIdflLWt9hXq5zbRPzFyvaQFNA"

# Referral (推荐)
$env:OMATE_REFERRAL_MEMBER_ID = "da73gddi57nmhr7pk160"

# Memory Sync Reporter (定时记忆同步, 秒)
$env:OMATE_MEMORY_SYNC_INTERVAL = "6000"

# OAuth2 SSO (GitHub)
$env:OMATE_OAUTH2_PROVIDER = "github"
$env:OMATE_OAUTH2_CLIENT_ID = "Ov23liNBeoGh1Z1GjOUs"
$env:OMATE_OAUTH2_CLIENT_SECRET = "699b4c85b73ab1ecddd271c7911285087bcf8f82"
$env:OMATE_OAUTH2_REDIRECT_URI = "http://localhost:8088/api/oauth/callback"

$env:UV_LINK_MODE = "copy"
cd "E:\workspace\github\QwenPaw"
uv run --python D:\python\312\python.exe qwenpaw app --host 0.0.0.0 --port 8088
