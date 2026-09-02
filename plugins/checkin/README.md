# Checkin Plugin

QwenPaw 个人每日签到插件，本地记录签到并自动计算连续天数和积分。配置远端后可同步签到记录到 a-console。

## 功能特性

- **一键签到** — 每日签到一次，自动计算连续天数和积分
- **幂等签到** — 每日只能签到一次，重复操作返回 `already: true`
- **积分规则** — 基础 10 分，连续签到 ≥ 7 天额外 +20 分（共 30 分）
- **远端同步** — 签到后自动推送到 a-console 的 `POST /admin/v1/checkin-records` 接口
- **签到记录** — 本地历史记录，支持分页查看
- **统计概览** — 今日状态、连续签到天数、累计签到天数

## 目录结构

```
plugins/checkin/
├── plugin.json              # 插件清单
├── backend/
│   └── plugin.py            # 后端 API（本地签到存储）
├── frontend/
│   ├── src/index.tsx         # React 前端（使用 host 提供的 antd）
│   ├── dist/index.js         # 构建产物
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── test_page.html            # 独立测试页面
├── dev_proxy.py              # 开发代理（8091 端口）
└── README.md
```

## 安装

```bash
# 使用 uv（必须）
uv run --python <python-path> qwenpaw plugin install plugins/checkin

# 热更新（运行中重新加载）
uv run --python <python-path> qwenpaw plugin install plugins/checkin --force
```

## API 端点

插件注册在 `/api/checkin` 前缀下：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/checkin/today` | 检查今日是否已签到 |
| POST | `/api/checkin/today` | 执行今日签到（幂等） |
| GET | `/api/checkin/history` | 查询本地签到历史（`?page=&size=`） |

### 响应示例

**GET /api/checkin/today**
```json
{
  "checked_in": false,
  "record": null,
  "date": "2026-08-26"
}
```

**POST /api/checkin/today**
```json
{
  "ok": true,
  "already": false,
  "record": {
    "date": "2026-08-26",
    "points_earned": 10,
    "consecutive_days": 1,
    "created_at": "2026-08-26T12:00:00"
  }
}
```

**GET /api/checkin/history?page=1&size=20**
```json
{
  "items": [
    {
      "date": "2026-08-26",
      "points_earned": 10,
      "consecutive_days": 3,
      "created_at": "2026-08-26T12:00:00"
    }
  ],
  "total": 3,
  "page": 1,
  "size": 20
}
```

## 环境变量

远端同步功能可选配置，不配置则仅本地记录。需在启动 QwenPaw **之前**设置：

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `OMATE_CONSOLE_URL` | 否 | 远程 a-console 服务地址，配置后启用远端同步 | `http://localhost:8080` |
| `OMATE_USER_TOKEN` | 同步必须 | Bearer Token（JWT），用户身份自动从 JWT 解析 | `eyJhbGci...` |

### 设置示例（PowerShell）

```powershell
$env:OMATE_CONSOLE_URL = "http://localhost:8080"
$env:OMATE_USER_TOKEN  = "<your-jwt-token>"
# 用户身份从 JWT 自动解析，无需传递人员参数

uv run --python D:\python\312\python.exe qwenpaw app --port 8088
```

### 远端同步流程

1. 本地签到成功 → 调用 `POST /admin/v1/checkin-records` 推送记录
2. a-console 将记录写入 `checkin_records` 表，同时更新会员积分和积分日志
3. 同步失败不影响本地签到（仅记录 warning 日志）
4. 响应中 `synced: true` 表示远端同步成功

签到数据本地存储在 `<workspace>/checkin_local.json`。

## 签到积分规则

| 条件 | 积分 |
|------|------|
| 每日签到 | 10 分 |
| 连续签到 ≥ 7 天 | 额外 +20 分（共 30 分） |

## 开发调试

```bash
# 启动开发代理（无需构建 console）
python plugins/checkin/dev_proxy.py

# 访问 http://127.0.0.1:8091 使用独立测试页面
```

### 前端构建

```bash
cd plugins/checkin/frontend
npx vite build
```
