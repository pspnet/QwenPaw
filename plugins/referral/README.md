# Referral Plugin

QwenPaw 推荐人插件 -- 邀请码生成、邀请记录查看、奖励统计。数据同步到 a-console 远端数据库。

## 功能特性

- **邀请码** — 显示当前会员的邀请码和邀请链接，支持一键复制
- **邀请记录** — 查看已接受邀请的人员列表，含奖励积分
- **奖励统计** — 累计邀请人数、累计获得奖励积分、当前积分余额
- **模拟邀请** — 内置"接受邀请"表单，方便测试

## API 端点

插件注册在 `/api/referral` 前缀下：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/referral/me` | 获取当前会员信息（含邀请码） |
| GET | `/api/referral/records` | 查询我的邀请记录（`?page=&size=`） |
| GET | `/api/referral/rewards` | 获取奖励统计 |
| POST | `/api/referral/accept` | 接受邀请（`?referral_code=&nickname=&user_id=`） |

## 环境变量

| 变量名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `QWENPAW_REFERRAL_REMOTE_URL` | 是 | 远程 a-console 服务地址 | `http://localhost:8080` |
| `QWENPAW_REFERRAL_TOKEN` | 是 | Bearer Token（JWT） | `eyJhbGci...` |
| `QWENPAW_REFERRAL_MEMBER_ID` | 是 | 远端会员 ID | `da73gddi57nmhr7pk160` |

## 积分规则

| 场景 | 积分 |
|------|------|
| 邀请成功（推荐人） | +50 积分 |
| 被邀请加入（被邀请人） | +20 积分 |

## a-console 远端接口

插件依赖 a-console 以下接口：

- `GET /admin/v1/members/:id` — 获取会员信息和邀请码
- `GET /admin/v1/referral-records?member_id=` — 查询邀请记录
- `POST /admin/v1/referral-records` — 接受邀请（创建推荐记录并发放积分）

## 开发调试

```bash
# 启动开发代理
python plugins/referral/dev_proxy.py

# 访问 http://127.0.0.1:8091
```

### 前端构建

```bash
cd plugins/referral/frontend
npx vite build
```
