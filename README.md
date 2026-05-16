# CloudPivot 云枢

> 云聚万物，一枢掌控

CloudPivot 是一个现代化、云原生、轻量级的 SSH 运维堡垒机平台，提供安全可靠的运维访问控制、会话审计、主机监控与 Docker 管理能力。

![](attachments/image-20260517051044950.png)

![](attachments/image-20260517051425649.png)

![](attachments/image-20260517051113948.png)

![](attachments/image-20260517051215097.png)

![](attachments/image-20260517051234236.png)

![](attachments/image-20260517051300013.png)

![](attachments/image-20260517051324532.png)

![](attachments/image-20260517051357515.png)

---

## 目录

- [技术栈](#技术栈)
- [核心功能](#核心功能)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [默认账号](#默认账号)
- [API 文档](#api-文档)
  - [认证说明](#认证说明)
  - [1. 认证模块](#1-认证模块-authcaptcha)
  - [2. 用户管理模块](#2-用户管理模块-users)
  - [3. 团队管理模块](#3-团队管理模块-teams)
  - [4. 主机管理模块](#4-主机管理模块-hosts)
  - [5. WebSSH 模块](#5-webssh-模块)
  - [6. 权限控制模块](#6-权限控制模块-permissions)
  - [7. Dashboard 模块](#7-dashboard-模块)
  - [8. 主机监控模块](#8-主机监控模块-monitor)
  - [9. Docker 管理模块](#9-docker-管理模块-docker)
  - [10. 会话审计模块](#10-会话审计模块-audit)
  - [11. SFTP 文件管理模块](#11-sftp-文件管理模块-sftp)
  - [12. 站点配置模块](#12-站点配置模块-site-config)
- [License](#license)

---

## 技术栈

### 后端

| 技术 | 说明 |
|------|------|
| **FastAPI** | 高性能异步 Python Web 框架 |
| **SQLAlchemy 2.0** | 异步 ORM |
| **Alembic** | 数据库迁移 |
| **asyncssh** | 异步 SSH 客户端 |
| **PostgreSQL** | 主数据库 |
| **Redis** | 缓存与消息队列 |
| **aiodocker** | 异步 Docker 客户端 |
| **python-jose** | JWT 认证 |
| **bcrypt** | 密码加密 |
| **loguru** | 日志记录 |

### 前端

| 技术 | 说明 |
|------|------|
| **Vue 3** + TypeScript | 响应式前端框架 |
| **TDesign Vue Next** | 企业级 UI 组件库 |
| **Pinia** | 状态管理 |
| **Vue I18n** | 国际化（中/英） |
| **xterm.js** | Web 终端 |
| **ECharts** | 图表可视化 |

---

## 核心功能

| 模块 | 功能 |
|------|------|
| 用户与团队 | 注册登录、团队 RBAC 管理、团队数据隔离、登录日志 |
| 主机资产 | SSH 主机 CRUD、分组标签、连通性检测、密码/密钥认证、批量导入 |
| WebSSH | 多标签终端、分屏、自动重连、文件上传、xterm.js + WebSocket |
| 权限控制 | 用户/团队至主机授权、临时授权与过期、细粒度(只读/上传/执行)、时间限制 |
| 会话审计 | 操作录屏回放、命令审计、风险命令检测(rm -rf 等)与拦截、导出 |
| 主机监控 | Agent 采集 CPU/内存/磁盘/网络、实时图表、告警规则 |
| Docker 管理 | 容器生命周期、日志/Stats/Exec、镜像管理 |
| Dashboard | 全局概览、资源使用率、风险告警、最近审计 |
| 告警系统 | 资源超限、异常登录、离线告警，邮件/飞书/钉钉/Webhook 通知 |
| SFTP 文件管理 | 远程文件浏览、上传下载、重命名/移动/复制/删除 |
| SSH 登录分析 | 自动采集 SSH 登录日志、暴力破解检测、新 IP 检测、趋势分析 |

---

## 项目结构

![设计思路](attachments/image-20260517052406716.png)

```
CloudPivot-Server/
├── main.py                     # FastAPI 入口
├── requirements.txt            # Python 依赖
├── alembic.ini                 # Alembic 配置
├── alembic/                    # 数据库迁移
├── Dockerfile                  # Docker 构建
├── docker-compose.yml          # Docker Compose 编排
├── .env.example                # 环境变量模板
├── app/
│   ├── config.py               # 全局配置 (pydantic-settings)
│   ├── database.py             # 数据库连接
│   ├── dependencies.py         # 依赖注入（认证）
│   ├── core/
│   │   ├── security.py         # JWT & 密码加密 & Token 黑名单
│   │   ├── ssh.py              # SSH 连接池
│   │   ├── websocket.py        # WebSocket 管理器
│   │   ├── docker_client.py    # Docker 客户端封装
│   │   ├── monitor_collector.py# 监控数据采集后台任务
│   │   ├── ssh_log_collector.py# SSH 登录日志采集
│   │   └── logger.py           # 日志配置 (loguru)
│   ├── models/                 # SQLAlchemy 数据模型
│   │   ├── user.py             # 用户、角色、状态
│   │   ├── team.py             # 团队、成员、角色
│   │   ├── host.py             # 主机、主机组、标签
│   │   ├── permission.py       # 主机权限、临时权限
│   │   ├── session.py          # SSH 会话、命令记录、录屏
│   │   ├── monitor.py          # 监控指标、告警规则、告警记录
│   │   ├── docker.py           # Docker 主机、容器信息
│   │   ├── log.py              # 登录日志、操作日志
│   │   ├── ssh_login_log.py    # SSH 登录日志（外部）
│   │   └── site_config.py      # 站点配置
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── routers/                # API 路由
│   │   ├── auth.py             # 认证（登录/注册/刷新/登出）
│   │   ├── captcha.py          # 验证码
│   │   ├── team.py             # 团队管理
│   │   ├── host.py             # 主机管理
│   │   ├── webssh.py           # WebSSH WebSocket
│   │   ├── permission.py       # 权限控制
│   │   ├── dashboard.py        # 仪表盘
│   │   ├── monitor.py          # 监控与告警
│   │   ├── docker.py           # Docker 管理
│   │   ├── audit.py            # 会话审计
│   │   ├── sftp.py             # SFTP 文件管理
│   │   └── site_config.py      # 站点配置
│   └── services/
│       └── notification.py     # 多渠道通知（邮件/飞书/钉钉/Webhook）
├── cloudpivot-web/             # 前端项目
│   ├── src/
│   │   ├── views/              # 页面视图
│   │   ├── layouts/            # 布局组件
│   │   ├── api/                # API 请求封装
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── router/             # 路由配置
│   │   └── locales/            # 国际化文件 (zh-CN / en)
│   ├── Dockerfile
│   └── nginx.conf
└── routers/                    # 辅助路由
```

---

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+

### 1. 克隆项目

```bash
git clone https://github.com/Moxin1044/CloudPivot.git
cd CloudPivot
```

### 2. 后端启动

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量
cp .env.example .env
# 编辑 .env 配置数据库等

# 启动服务（开发模式自动建表）
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端启动

```bash
cd cloudpivot-web

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### 4. Docker 部署（推荐）

```bash
# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 初始化数据库
docker-compose exec backend alembic upgrade head
```

### 5. 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "init tables"

# 执行迁移
alembic upgrade head
```

---

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用名称 | CloudPivot |
| `APP_ENV` | 运行环境 (development/production) | development |
| `APP_DEBUG` | 调试模式 | true |
| `APP_SECRET_KEY` | 应用密钥 | change-me-to-a-random-secret-key |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 过期时间(分钟) | 480 |
| `APP_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 过期时间(天) | 7 |
| `APP_HOST` | 监听地址 | 0.0.0.0 |
| `APP_PORT` | 监听端口 | 8000 |
| `DATABASE_URL` | PostgreSQL 连接串 | postgresql+asyncpg://cloudpivot:cloudpivot@localhost:5432/cloudpivot |
| `REDIS_URL` | Redis 连接串 | redis://localhost:6379/0 |
| `DOCKER_HOST` | Docker Socket | unix:///var/run/docker.sock |
| `SMTP_HOST` | 邮件服务器 | - |
| `SMTP_PORT` | 邮件端口 | 465 |
| `SMTP_USER` | 邮件用户 | - |
| `SMTP_PASSWORD` | 邮件密码 | - |
| `SMTP_FROM` | 发件人 | - |
| `WEBSSH_SSH_TIMEOUT` | SSH 连接超时(秒) | 30 |
| `WEBSSH_MAX_SESSIONS_PER_USER` | 每用户最大会话数 | 5 |
| `AGENT_SECRET_KEY` | Agent 认证密钥 | agent-secret-key-change-me |
| `CAPTCHA_ENABLED` | 验证码开关 | true |
| `CAPTCHA_EXPIRE_SECONDS` | 验证码过期(秒) | 300 |
| `LOGIN_MAX_ATTEMPTS` | 最大登录尝试次数 | 5 |
| `LOGIN_LOCKOUT_MINUTES` | 登录锁定时间(分钟) | 15 |
| `LOG_LEVEL` | 日志级别 | INFO |
| `DEFAULT_ADMIN_USERNAME` | 默认管理员用户名 | admin |
| `DEFAULT_ADMIN_PASSWORD` | 默认管理员密码 | admin123 |
| `DEFAULT_ADMIN_EMAIL` | 默认管理员邮箱 | admin@cloudpivot.localhost |

---

## 默认账号

首次运行自动创建管理员账号：`admin` / `admin123`

注册功能可通过站点配置 `allow_register` 控制开关。

---

## API 文档

启动后访问在线文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**所有 API 基础路径**: `/api/v1`

### 认证说明

除公开接口外，所有请求需在 Header 中携带 JWT Token：

```
Authorization: Bearer <access_token>
```

**权限级别说明**：
- 🔓 公开 — 无需认证
- 🔑 登录用户 — 需要 `get_current_user`
- 👑 管理员 — 需要 `get_current_active_admin`

---

### 1. 认证模块 (`/auth` + `/auth/captcha`)

#### GET `/auth/captcha` 🔓

获取验证码图片，返回 SVG base64 编码的验证码。验证码一次性使用，默认有效期 300 秒。

**响应**：

```json
{
  "captcha_id": "uuid-string",
  "captcha_image": "data:image/svg+xml;base64,..."
}
```

#### POST `/auth/register` 🔓

用户注册。受站点配置 `allow_register` 控制。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✅ | 3-64字符 |
| email | string | ✅ | 邮箱 |
| password | string | ✅ | 6-128字符 |
| display_name | string | ❌ | 显示名，默认同 username |

**响应**：`UserResponse`

```json
{
  "id": 2,
  "username": "newuser",
  "email": "user@example.com",
  "display_name": "New User",
  "role": "viewer",
  "status": "active",
  "language": "zh-CN",
  "theme": "light",
  "avatar_url": null,
  "notification_email": null,
  "feishu_webhook": null,
  "dingtalk_webhook": null,
  "notify_channels": null,
  "last_login_at": null,
  "last_login_ip": null,
  "created_at": "2026-05-17T05:00:00+00:00",
  "updated_at": "2026-05-17T05:00:00+00:00"
}
```

#### POST `/auth/login` 🔓

用户登录，返回 JWT 令牌对。连续失败超过 `LOGIN_MAX_ATTEMPTS` 次后锁定 `LOGIN_LOCKOUT_MINUTES` 分钟。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✅ | 3-64字符 |
| password | string | ✅ | 6-128字符 |
| captcha_id | string | ❌ | 验证码 ID（CAPTCHA_ENABLED=true 时必填） |
| captcha_code | string | ❌ | 验证码（CAPTCHA_ENABLED=true 时必填） |

**响应**：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

**错误码**：
- `400` — 验证码无效
- `401` — 用户名或密码错误
- `403` — 账号已禁用
- `429` — 登录尝试次数过多，已锁定

#### POST `/auth/refresh` 🔓

使用 Refresh Token 换取新的令牌对（Rotation 模式，旧 Token 加入黑名单）。若用户 `token_version` 已变更（如修改密码后），则 Refresh Token 失效，需重新登录。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| refresh_token | string | ✅ | Refresh Token |

**响应**：同登录响应 `TokenResponse`

**错误码**：
- `401` — Token 已撤销 / 无效 / 版本不匹配 / 用户不存在或已禁用

#### POST `/auth/logout` 🔑

登出，将当前 Access Token 加入黑名单。

**请求头**：`Authorization: Bearer <access_token>`

**响应**：`{"message": "Logged out successfully"}`

---

### 2. 用户管理模块 (`/users`)

#### GET `/users/me` �

获取当前登录用户信息。

**响应**：`UserResponse`

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@cloudpivot.localhost",
  "display_name": "Super Admin",
  "role": "admin",
  "status": "active",
  "language": "zh-CN",
  "theme": "light",
  "avatar_url": null,
  "notification_email": null,
  "feishu_webhook": null,
  "dingtalk_webhook": null,
  "notify_channels": null,
  "last_login_at": "2026-05-17T04:30:00+00:00",
  "last_login_ip": "127.0.0.1",
  "created_at": "2026-05-17T00:00:00+00:00",
  "updated_at": "2026-05-17T04:30:00+00:00"
}
```

#### PUT `/users/me` 🔑

更新当前用户信息。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | ❌ | 邮箱 |
| display_name | string | ❌ | 显示名 |
| language | string | ❌ | 语言 (zh-CN/en) |
| theme | string | ❌ | 主题 (light/dark) |
| password | string | ❌ | 新密码 (6-128字符) |
| role | string | ❌ | 角色 (admin/viewer) |
| status | string | ❌ | 状态 (active/disabled) |

**响应**：`UserResponse`

#### PUT `/users/me/notifications` 🔑

更新个人通知渠道配置。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| notification_email | string | ❌ | 通知邮箱 |
| feishu_webhook | string | ❌ | 飞书 Webhook URL |
| dingtalk_webhook | string | ❌ | 钉钉 Webhook URL |
| notify_channels | string | ❌ | 通知渠道，逗号分隔 (email,feishu,dingtalk,webhook) |

**响应**：`UserResponse`

#### PUT `/users/me/password` 🔑

修改密码。修改后 `token_version` 递增，所有已有 Token（包括 Refresh Token）立即失效，需重新登录。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| old_password | string | ✅ | 旧密码 |
| new_password | string | ✅ | 新密码 (6-128字符) |

**响应**：`{"message": "Password changed successfully"}`

**错误码**：`400` — 旧密码不正确

#### GET `/users` 👑

获取用户列表（仅管理员）。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| skip | int | 偏移量 (默认0) |
| limit | int | 每页数量 (默认20) |
| role | string | 按角色筛选 (admin/viewer) |
| status | string | 按状态筛选 (active/disabled) |
| search | string | 搜索 (匹配用户名/邮箱/显示名) |

**响应**：`list[UserResponse]`

#### POST `/users` 👑

创建用户（仅管理员）。

**请求体** (`UserCreate`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | ✅ | 3-64字符 |
| email | string | ✅ | 邮箱 |
| password | string | ✅ | 6-128字符 |
| display_name | string | ❌ | 显示名，默认同 username |
| role | string | ❌ | 角色 (admin/viewer，默认viewer) |
| status | string | ❌ | 状态 (默认active) |
| language | string | ❌ | 默认 zh-CN |
| theme | string | ❌ | 默认 light |

**响应**：`UserResponse` (201)

**错误码**：`400` — 用户名或邮箱已存在

#### GET `/users/{user_id}` 👑

获取指定用户详情。

**路径参数**：`user_id` (int)

**响应**：`UserResponse`

**错误码**：`404` — 用户不存在

#### PUT `/users/{user_id}` 👑

更新指定用户信息。

**路径参数**：`user_id` (int)

**请求体**：`UserUpdate`（所有字段可选，同上）

**响应**：`UserResponse`

**错误码**：`404` — 用户不存在

#### DELETE `/users/{user_id}` 👑

删除用户。不能删除自己。

**路径参数**：`user_id` (int)

**响应**：`{"message": "User deleted"}`

**错误码**：
- `400` — 不能删除自己
- `404` — 用户不存在

---

### 3. 团队管理模块 (`/teams`)

#### GET `/teams` 🔑

获取团队列表。管理员查看所有团队，普通用户仅查看自己所属团队。

**查询参数**：`skip` (默认0), `limit` (默认20)

**响应**：`list[TeamResponse]`

```json
[
  {
    "id": 1,
    "name": "运维团队",
    "description": "负责生产环境运维",
    "avatar_url": null,
    "is_active": true,
    "created_at": "2026-05-17T00:00:00+00:00"
  }
]
```

#### POST `/teams` 🔑

创建团队。创建者自动成为 Owner。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 团队名 (1-128字符) |
| description | string | ❌ | 描述 |

**响应**：`TeamResponse` (201)

#### GET `/teams/{team_id}` 🔑

获取团队详情。非成员返回 403。

**路径参数**：`team_id` (int)

**响应**：`TeamResponse`

**错误码**：`403` — 非团队成员, `404` — 团队不存在

#### PUT `/teams/{team_id}` 🔑

更新团队信息。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ❌ | 团队名 (1-128字符) |
| description | string | ❌ | 描述 |

**响应**：`TeamResponse`

#### DELETE `/teams/{team_id}` 👑

删除团队（仅管理员）。

**响应**：`{"message": "Team deleted"}`

#### GET `/teams/{team_id}/members` 🔑

获取团队成员列表。

**响应**：`list[TeamMemberResponse]`

```json
[
  {
    "id": 1,
    "team_id": 1,
    "user_id": 1,
    "role": "owner",
    "joined_at": "2026-05-17T00:00:00+00:00",
    "username": "admin",
    "display_name": "Super Admin",
    "email": "admin@cloudpivot.localhost"
  }
]
```

#### POST `/teams/{team_id}/members` 🔑

添加团队成员。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | ✅ | 用户 ID |
| role | string | ❌ | 角色 (owner/admin/member/viewer，默认viewer) |

**响应**：`TeamMemberResponse` (201)

**错误码**：
- `400` — 用户已是成员
- `404` — 用户不存在

#### PUT `/teams/{team_id}/members/{user_id}` 🔑

更新成员角色。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| role | string | ✅ | 新角色 (owner/admin/member/viewer) |

**响应**：`TeamMemberResponse`

**错误码**：`404` — 成员不存在

#### DELETE `/teams/{team_id}/members/{user_id}` 🔑

移除团队成员。不能移除 Owner。

**响应**：`{"message": "Member removed"}`

**错误码**：
- `400` — 不能移除 Owner
- `404` — 成员不存在

---

### 4. 主机管理模块 (`/hosts`)

#### GET `/hosts` 🔑

获取主机列表（分页）。管理员查看所有主机，普通用户仅查看有权限的主机。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| skip | int | 偏移量 (默认0) |
| limit | int | 每页数量 (默认20) |
| group_id | int | 按主机组筛选 |
| status | string | 按状态筛选 (online/offline/unknown) |
| keyword | string | 搜索关键词 (匹配名称/IP/主机名/OS/公网IP) |

**响应**：

```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "name": "web-server-01",
      "hostname": "web01",
      "ip_address": "192.168.1.10",
      "port": 22,
      "auth_type": "password",
      "username": "root",
      "status": "online",
      "os_info": "Ubuntu 22.04",
      "os_name": "Ubuntu",
      "os_version": "22.04",
      "public_ip": "1.2.3.4",
      "description": "Web 前端服务器",
      "team_id": null,
      "group_id": 1,
      "tags": [
        {"id": 1, "name": "生产环境", "color": "#e02424"}
      ],
      "last_connected_at": "2026-05-17T04:30:00+00:00",
      "created_at": "2026-05-17T00:00:00+00:00",
      "updated_at": "2026-05-17T04:30:00+00:00"
    }
  ]
}
```

#### POST `/hosts` 🔑

添加主机。

**请求体** (`HostCreate`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 主机名 (1-128) |
| hostname | string | ✅ | 主机标识 |
| ip_address | string | ✅ | IP 地址 |
| port | int | ❌ | SSH 端口 (默认22) |
| auth_type | string | ❌ | 认证方式 (password/key，默认password) |
| username | string | ✅ | SSH 用户名 |
| password | string | ❌ | SSH 密码 (password 认证时使用) |
| private_key | string | ❌ | SSH 私钥 (key 认证时使用) |
| description | string | ❌ | 描述 |
| public_ip | string | ❌ | 公网 IP |
| os_name | string | ❌ | 系统名 |
| os_version | string | ❌ | 系统版本 |
| team_id | int | ❌ | 所属团队 ID |
| group_id | int | ❌ | 所属主机组 ID |
| tag_ids | list[int] | ❌ | 标签 ID 列表 |

**响应**：`HostResponse` (201)

#### POST `/hosts/batch-import` 👑

批量导入主机（仅管理员）。

**请求体**：

```json
{
  "hosts": [
    {
      "name": "server-01",
      "hostname": "srv01",
      "ip_address": "192.168.1.10",
      "username": "root",
      "password": "secret"
    },
    {
      "name": "server-02",
      "hostname": "srv02",
      "ip_address": "192.168.1.11",
      "username": "root",
      "auth_type": "key",
      "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n..."
    }
  ]
}
```

**响应**：

```json
{
  "message": "Imported 2 hosts",
  "hosts": ["server-01", "server-02"]
}
```

#### GET `/hosts/{host_id}` 🔑

获取主机详情。

**路径参数**：`host_id` (int)

**响应**：`HostResponse`

**错误码**：`404` — 主机不存在

#### GET `/hosts/{host_id}/metrics` 🔑

获取主机监控图表数据。

**路径参数**：`host_id` (int)

**查询参数**：`hours` (默认24，取最近 N 小时的监控数据)

**响应**：

```json
[
  {
    "collected_at": "2026-05-17T05:00:00+00:00",
    "cpu_percent": 45.2,
    "memory_percent": 68.1,
    "disk_percent": 52.0,
    "network_in_kbps": 1024.5,
    "network_out_kbps": 512.3,
    "load_1min": 1.25
  }
]
```

#### PUT `/hosts/{host_id}` 🔑

更新主机信息。

**请求体**：`HostUpdate`（同 HostCreate，所有字段可选）

**响应**：`HostResponse`

**错误码**：`404` — 主机不存在

#### DELETE `/hosts/{host_id}` 🔑

删除主机。

**响应**：`{"message": "Host deleted"}`

**错误码**：`404` — 主机不存在

#### POST `/hosts/{host_id}/test` 🔑

测试主机 SSH 连通性。成功时自动获取公网 IP、OS 信息并更新主机记录。

**响应** (`ConnectivityTestResult`)：

```json
{
  "host_id": 1,
  "success": true,
  "message": "Connected successfully",
  "latency_ms": 45.32
}
```

**失败响应**：

```json
{
  "host_id": 1,
  "success": false,
  "message": "Connection refused",
  "latency_ms": null
}
```

#### GET `/hosts/groups/list` 🔑

获取主机组列表（含每组主机数量）。

**响应**：`list[HostGroupResponse]`

```json
[
  {
    "id": 1,
    "name": "生产环境",
    "description": "生产环境服务器组",
    "parent_id": null,
    "host_count": 5,
    "created_at": "2026-05-17T00:00:00+00:00"
  }
]
```

#### POST `/hosts/groups` 🔑

创建主机组。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 组名 (1-128) |
| description | string | ❌ | 描述 |
| parent_id | int | ❌ | 父组 ID（支持嵌套分组） |

**响应**：`HostGroupResponse` (201)

#### GET `/hosts/tags/list` 🔑

获取标签列表。

**响应**：`list[HostTagResponse]`

```json
[
  {
    "id": 1,
    "name": "生产环境",
    "color": "#e02424",
    "created_at": "2026-05-17T00:00:00+00:00"
  }
]
```

#### POST `/hosts/tags` 🔑

创建标签。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 标签名 (1-64) |
| color | string | ❌ | 颜色 (默认 #1890ff) |

**响应**：`HostTagResponse` (201)

---

### 5. WebSSH 模块

#### WebSocket `/ws/ssh/{host_id}`

WebSSH 终端连接。通过 WebSocket 建立 SSH 交互通道。

**连接方式**：`ws://localhost:8000/api/v1/ws/ssh/{host_id}?token=<access_token>`

**路径参数**：`host_id` (int)

**查询参数**：`token` (必填，Access Token)

**消息格式**（客户端 → 服务端）：

```json
// 输入字符
{"type": "input", "data": "ls -la\n"}

// 调整终端尺寸
{"type": "resize", "cols": 120, "rows": 40}

// 心跳
{"type": "ping"}
```

**消息格式**（服务端 → 客户端）：

```json
// 连接成功
{"_sys": true, "type": "connected", "session_id": "uuid", "host": "192.168.1.1", "username": "root"}

// 命令被拦截
{"_sys": true, "type": "blocked", "command": "rm -rf /", "risk": "danger", "message": "Command blocked (risk: danger)"}

// 心跳响应
{"_sys": true, "type": "pong"}

// SSH 输出 — 直接发送纯文本/二进制数据
```

**权限级别与命令控制**：

| 权限级别 | 允许的操作 |
|----------|-----------|
| `readonly` | 仅允许查看命令（cat, ls, pwd, whoami, df, free, top, ps 等） |
| `read_execute` | 允许执行命令（受风险检测约束） |
| `read_write` | 完全读写权限 |
| `full` | 完全权限 |

> 当 `can_execute=false` 时，非安全命令将被拦截；当 `can_upload=false` 时，scp/rsync/rz/sz/sftp 命令将被拦截。

**风险命令等级**：
- `danger` — 拦截：`rm -rf /`, `mkfs`, `dd if=`, `shutdown`, `reboot`, `init 0/6`, `chmod -R 777 /` 等
- `warning` — 警告：`rm -rf`, `kill -9`, `iptables -F`, `systemctl stop/disable`, `userdel` 等
- `safe` — 安全

**关闭码**：
- `4001` — 认证失败
- `4003` — 用户不存在或已禁用
- `4004` — 主机不存在
- `4005` — 会话数达到上限（默认5）
- `4006` — SSH 连接失败

#### GET `/sessions` 🔑

获取 SSH 会话列表。管理员查看全部，普通用户仅查看自己的会话。

**查询参数**：`skip` (默认0), `limit` (默认20)

**响应**：SSH 会话列表

#### GET `/sessions/{session_id}/commands` 🔑

获取会话命令记录。

**路径参数**：`session_id` (int，数据库 ID)

**查询参数**：`skip` (默认0), `limit` (默认100)

**响应**：命令记录列表

#### GET `/sessions/{session_id}/recording` 🔑

获取会话录屏记录。

**路径参数**：`session_id` (int，数据库 ID)

**响应**：录屏记录对象

**错误码**：`404` — 录屏不存在

#### GET `/active-sessions` 🔑

获取当前活跃的 SSH 会话列表。

**响应**：活跃会话列表

---

### 6. 权限控制模块 (`/permissions`)

#### GET `/permissions` 🔑

获取权限列表，支持按 host_id / team_id / user_id 筛选。普通用户仅查看所属团队的权限。

**查询参数**：`host_id` (int), `team_id` (int), `user_id` (int)

**响应**：`list[HostPermissionResponse]`

```json
[
  {
    "id": 1,
    "host_id": 1,
    "team_id": 1,
    "user_id": null,
    "permission_level": "read_execute",
    "can_upload": false,
    "can_download": true,
    "can_execute": true,
    "allowed_time_start": "09:00",
    "allowed_time_end": "18:00",
    "allowed_days": "1,2,3,4,5",
    "is_active": true,
    "created_at": "2026-05-17T00:00:00+00:00"
  }
]
```

#### POST `/permissions` 🔑

创建主机权限。必须指定 `team_id` 或 `user_id`（至少一个）。

**请求体** (`HostPermissionCreate`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| host_id | int | ✅ | 主机 ID |
| team_id | int | ❌ | 团队 ID (与 user_id 至少填一个) |
| user_id | int | ❌ | 用户 ID (与 team_id 至少填一个) |
| permission_level | string | ❌ | 权限级别 (readonly/read_execute/read_write/full，默认read_execute) |
| can_upload | bool | ❌ | 允许上传 (默认false) |
| can_download | bool | ❌ | 允许下载 (默认false) |
| can_execute | bool | ❌ | 允许执行 (默认true) |
| allowed_time_start | string | ❌ | 允许时段开始 (如 "09:00") |
| allowed_time_end | string | ❌ | 允许时段结束 (如 "18:00") |
| allowed_days | string | ❌ | 允许星期 (如 "1,2,3,4,5"，1=周一) |

**响应**：`HostPermissionResponse` (201)

**错误码**：
- `400` — 必须指定 team_id 或 user_id
- `404` — 主机不存在

#### PUT `/permissions/{perm_id}` 🔑

更新权限。

**路径参数**：`perm_id` (int)

**请求体** (`HostPermissionUpdate`，所有字段可选)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| permission_level | string | ❌ | 权限级别 |
| can_upload | bool | ❌ | 允许上传 |
| can_download | bool | ❌ | 允许下载 |
| can_execute | bool | ❌ | 允许执行 |
| allowed_time_start | string | ❌ | 允许时段开始 |
| allowed_time_end | string | ❌ | 允许时段结束 |
| allowed_days | string | ❌ | 允许星期 |
| is_active | bool | ❌ | 是否启用 |

**响应**：`HostPermissionResponse`

**错误码**：`404` — 权限不存在

#### DELETE `/permissions/{perm_id}` 🔑

删除权限。

**响应**：`{"message": "Permission deleted"}`

**错误码**：`404` — 权限不存在

#### GET `/permissions/temporary` 🔑

获取临时授权列表（仅未撤销且未过期的）。

**查询参数**：`user_id` (int，可选)

**响应**：`list[TemporaryPermissionResponse]`

```json
[
  {
    "id": 1,
    "host_id": 1,
    "user_id": 2,
    "granted_by": 1,
    "permission_level": "read_execute",
    "reason": "紧急运维需求",
    "expires_at": "2026-05-18T00:00:00+00:00",
    "is_revoked": false,
    "created_at": "2026-05-17T05:00:00+00:00"
  }
]
```

#### POST `/permissions/temporary` 🔑

创建临时授权。

**请求体** (`TemporaryPermissionCreate`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| host_id | int | ✅ | 主机 ID |
| user_id | int | ✅ | 用户 ID |
| permission_level | string | ❌ | 权限级别 (默认read_execute) |
| reason | string | ❌ | 授权原因 |
| expires_at | datetime | ✅ | 过期时间 (必须在未来) |

**响应**：`TemporaryPermissionResponse` (201)

**错误码**：`400` — 过期时间必须在将来

#### POST `/permissions/temporary/{perm_id}/revoke` 🔑

撤销临时授权。

**路径参数**：`perm_id` (int)

**响应**：`{"message": "Temporary permission revoked"}`

**错误码**：`404` — 临时权限不存在

---

### 7. Dashboard 模块 (`/dashboard`)

#### GET `/dashboard` 🔑

获取 Dashboard 数据。管理员查看全局，普通用户仅查看有权限主机的数据。

**响应** (`DashboardResponse`)：

```json
{
  "overview": {
    "total_hosts": 50,
    "online_hosts": 45,
    "offline_hosts": 5,
    "active_sessions": 3,
    "total_users": 10,
    "active_alerts": 2,
    "risk_commands_today": 7
  },
  "resource_usage": [
    {
      "host_id": 1,
      "host_name": "web-server-01",
      "cpu_percent": 45.2,
      "memory_percent": 68.1,
      "disk_percent": 52.0
    }
  ],
  "recent_audits": [
    {
      "session_id": "uuid-string",
      "username": "admin",
      "host_name": "web-server-01",
      "command": "ls -la",
      "risk_level": "safe",
      "executed_at": "2026-05-17T05:00:00+00:00"
    }
  ],
  "recent_alerts": [
    {
      "id": 1,
      "title": "CPU 使用率过高",
      "severity": "warning",
      "created_at": "2026-05-17T04:30:00+00:00"
    }
  ]
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| overview.total_hosts | 有权限的主机总数 |
| overview.online_hosts | 在线主机数 |
| overview.offline_hosts | 离线主机数 |
| overview.active_sessions | 活跃 SSH 会话数 |
| overview.total_users | 系统用户总数（仅管理员可见） |
| overview.active_alerts | 待处理告警数 |
| overview.risk_commands_today | 今日风险命令数 |
| resource_usage | Top 10 主机资源使用率 |
| recent_audits | 最近 10 条审计记录 |
| recent_alerts | 最近 10 条告警记录 |

---

### 8. 主机监控模块 (`/monitor`)

#### GET `/monitor/metrics/{host_id}` 🔑

获取主机监控指标（时间序列）。

**路径参数**：`host_id` (int)

**查询参数**：`hours` (默认1，最近 N 小时)

**响应**：`list[HostMetricResponse]`

```json
[
  {
    "id": 100,
    "host_id": 1,
    "cpu_percent": 45.2,
    "memory_percent": 68.1,
    "memory_used_gb": 10.9,
    "memory_total_gb": 16.0,
    "disk_percent": 52.0,
    "disk_used_gb": 104.0,
    "disk_total_gb": 200.0,
    "network_in_kbps": 1024.5,
    "network_out_kbps": 512.3,
    "load_1min": 1.25,
    "load_5min": 1.10,
    "load_15min": 0.95,
    "collected_at": "2026-05-17T05:00:00+00:00"
  }
]
```

#### GET `/monitor/metrics/{host_id}/latest` 🔑

获取主机最新一条监控指标。

**路径参数**：`host_id` (int)

**响应**：`HostMetricResponse | null`

#### GET `/monitor/alert-rules` 🔑

获取告警规则列表。

**响应**：`list[AlertRuleResponse]`

#### POST `/monitor/alert-rules` 🔑

创建告警规则。

**请求体** (`AlertRuleCreate`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 规则名 |
| description | string | ❌ | 描述 |
| metric_type | string | ✅ | 指标类型 (cpu_percent/memory_percent/disk_percent/network_in_kbps/network_out_kbps/load_1min) |
| condition | string | ✅ | 比较条件 (gt/lt/gte/lte/eq) |
| threshold | float | ✅ | 阈值 |
| duration_seconds | int | ❌ | 持续时间 (默认0) |
| severity | string | ❌ | 严重级别 (info/warning/critical，默认warning) |
| host_id | int | ❌ | 主机 ID (为空则全局) |
| team_id | int | ❌ | 团队 ID |
| notify_channels | list | ❌ | 通知渠道 |
| webhook_url | string | ❌ | Webhook URL |
| is_enabled | bool | ❌ | 是否启用 (默认true) |

**响应**：`AlertRuleResponse` (201)

```json
{
  "id": 1,
  "name": "CPU 过高告警",
  "description": "CPU 使用率超过 90%",
  "metric_type": "cpu_percent",
  "condition": "gt",
  "threshold": 90.0,
  "duration_seconds": 0,
  "severity": "warning",
  "host_id": null,
  "team_id": null,
  "notify_channels": ["email"],
  "webhook_url": null,
  "is_enabled": true,
  "created_at": "2026-05-17T00:00:00+00:00"
}
```

#### PUT `/monitor/alert-rules/{rule_id}` 🔑

更新告警规则。

**路径参数**：`rule_id` (int)

**请求体**：同 `AlertRuleCreate`

**响应**：`AlertRuleResponse`

**错误码**：`404` — 规则不存在

#### DELETE `/monitor/alert-rules/{rule_id}` 🔑

删除告警规则。

**响应**：`{"message": "Alert rule deleted"}`

**错误码**：`404` — 规则不存在

#### GET `/monitor/alerts` 🔑

获取告警记录列表。

**查询参数**：`severity` (info/warning/critical), `status` (pending/acknowledged/resolved), `skip` (默认0), `limit` (默认20)

**响应**：`list[AlertRecordResponse]`

```json
[
  {
    "id": 1,
    "rule_id": 1,
    "host_id": 1,
    "severity": "warning",
    "status": "pending",
    "title": "CPU 过高告警 - cpu_percent gt 90",
    "message": "Current value: 95.2",
    "notified_channels": ["email"],
    "acknowledged_by": null,
    "acknowledged_at": null,
    "resolved_at": null,
    "created_at": "2026-05-17T04:30:00+00:00"
  }
]
```

#### POST `/monitor/alerts/{alert_id}/acknowledge` 🔑

确认告警。将状态从 `pending` 变更为 `acknowledged`。

**响应**：`{"message": "Alert acknowledged"}`

**错误码**：`404` — 告警不存在

#### POST `/monitor/alerts/{alert_id}/resolve` 🔑

解决告警。将状态变更为 `resolved`。

**响应**：`{"message": "Alert resolved"}`

**错误码**：`404` — 告警不存在

#### POST `/monitor/agent/report` 🔓

Agent 上报监控数据（内部接口，供 cloudpivot-agent 调用）。上报后自动检查告警规则并触发通知。

**请求体**：

```json
{
  "host_id": 1,
  "cpu_percent": 45.2,
  "memory_percent": 68.1,
  "memory_used_gb": 10.9,
  "memory_total_gb": 16.0,
  "disk_percent": 52.0,
  "disk_used_gb": 104.0,
  "disk_total_gb": 200.0,
  "network_in_kbps": 1024.5,
  "network_out_kbps": 512.3,
  "load_1min": 1.25,
  "load_5min": 1.10,
  "load_15min": 0.95,
  "extra_data": {}
}
```

**响应**：`{"status": "ok"}`

**错误码**：`400` — host_id 必填

---

### 9. Docker 管理模块 (`/docker`)

#### GET `/docker/hosts` 🔑

获取 Docker 主机列表。

**响应**：`list[DockerHostResponse]`

```json
[
  {
    "id": 1,
    "name": "本地 Docker",
    "host": "unix:///var/run/docker.sock",
    "host_id": null,
    "team_id": null,
    "tls_verify": false,
    "is_active": true,
    "version_info": {"ApiVersion": "1.43"},
    "created_at": "2026-05-17T00:00:00+00:00"
  }
]
```

#### POST `/docker/hosts` 🔑

添加 Docker 主机。

**请求体** (`DockerHostCreate`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 主机名称 |
| host | string | ✅ | Docker 连接地址 (如 unix:///var/run/docker.sock 或 tcp://192.168.1.10:2376) |
| host_id | int | ❌ | 关联的 SSH 主机 ID |
| team_id | int | ❌ | 所属团队 ID |
| tls_verify | bool | ❌ | 是否验证 TLS (默认false) |
| cert_path | string | ❌ | TLS 证书路径 |

**响应**：`DockerHostResponse` (201)

#### DELETE `/docker/hosts/{host_id}` 🔑

删除 Docker 主机。

**路径参数**：`host_id` (int)

**响应**：`{"message": "Docker host deleted"}`

**错误码**：`404` — Docker 主机不存在

#### GET `/docker/containers` 🔑

获取容器列表。

**查询参数**：`all` (默认false，true 时包含已停止的容器)

**响应**：`list[ContainerResponse]`

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "nginx",
    "image": "nginx:latest",
    "status": "Up 2 hours",
    "state": "running",
    "ports": [{"PublicPort": 80, "PrivatePort": 80, "Type": "tcp"}],
    "labels": {"maintainer": "NGINX Docker Maintainers"},
    "created": 1715923200
  }
]
```

#### GET `/docker/containers/{container_id}` 🔑

获取容器详情。

**路径参数**：`container_id` (string，容器 ID 或名称)

**响应**：容器详细信息

#### POST `/docker/containers/{container_id}/start` 🔑

启动容器。

**响应**：`{"message": "Container xxx started"}`

#### POST `/docker/containers/{container_id}/stop` 🔑

停止容器。

**请求体** (可选)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| timeout | int | ❌ | 停止超时秒数 (默认10) |

**响应**：`{"message": "Container xxx stopped"}`

#### POST `/docker/containers/{container_id}/restart` 🔑

重启容器。

**请求体** (可选)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| timeout | int | ❌ | 重启超时秒数 (默认10) |

**响应**：`{"message": "Container xxx restarted"}`

#### DELETE `/docker/containers/{container_id}` 🔑

删除容器。

**查询参数**：`force` (默认false，是否强制删除)

**响应**：`{"message": "Container xxx removed"}`

#### GET `/docker/containers/{container_id}/logs` 🔑

获取容器日志。

**查询参数**：`tail` (默认100，最后 N 行)

**响应** (`ContainerLogResponse`)：

```json
{
  "logs": "log line 1\nlog line 2\n..."
}
```

#### GET `/docker/containers/{container_id}/stats` 🔑

获取容器资源使用统计（实时采样）。

**响应** (`ContainerStatsResponse`)：

```json
{
  "cpu_percent": 2.35,
  "memory_usage_mb": 128.5,
  "memory_limit_mb": 1024.0,
  "memory_percent": 12.55,
  "network_in_bytes": null,
  "network_out_bytes": null,
  "block_read_bytes": null,
  "block_write_bytes": null,
  "pids": 12
}
```

#### POST `/docker/containers/{container_id}/exec` 🔑

在容器内执行命令。

**请求体** (`ExecRequest`)：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| command | string | ✅ | 执行命令 |
| tty | bool | ❌ | 是否分配 TTY (默认true) |

**响应**：

```json
{
  "exec_id": "...",
  "message": "Command executed"
}
```

#### GET `/docker/images` 🔑

获取镜像列表。

**响应**：`list[ImageResponse]`

```json
[
  {
    "id": "sha256:a1b2c3d4...",
    "repo_tags": ["nginx:latest", "nginx:1.25"],
    "size_mb": 187.64,
    "created": 1715923200
  }
]
```

#### POST `/docker/images/pull` 🔑

拉取镜像。

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repository | string | ✅ | 镜像仓库名 (如 nginx) |
| tag | string | ❌ | 标签 (默认latest) |

**响应**：`{"message": "Image nginx:latest pulled"}`

#### DELETE `/docker/images/{image_id}` 🔑

删除镜像。

**查询参数**：`force` (默认false，是否强制删除)

**响应**：`{"message": "Image xxx removed"}`

#### GET `/docker/info` 🔑

获取 Docker 系统信息和版本。

**响应**：

```json
{
  "info": {
    "Containers": 5,
    "Images": 10,
    "ServerVersion": "24.0.7",
    "OperatingSystem": "Ubuntu 22.04"
  },
  "version": {
    "Version": "24.0.7",
    "ApiVersion": "1.43"
  }
}
```

---

### 10. 会话审计模块 (`/audit`)

#### GET `/audit/sessions` 🔑

获取会话审计列表（分页）。普通用户仅查看有权限主机会话。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| skip | int | 偏移量 (默认0) |
| limit | int | 每页数量 (默认20) |
| user_id | int | 按用户筛选 |
| host_id | int | 按主机筛选 |
| status | string | 按状态筛选 (active/closed) |
| keyword | string | 搜索 (匹配 session_id/client_ip) |

**响应**：

```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "session_id": "uuid-string",
      "user_id": 1,
      "host_id": 1,
      "client_ip": "192.168.1.100",
      "status": "closed",
      "started_at": "2026-05-17T04:00:00+00:00",
      "ended_at": "2026-05-17T04:30:00+00:00",
      "duration_seconds": 1800
    }
  ]
}
```

#### GET `/audit/commands` 🔑

获取命令审计列表（分页）。普通用户仅查看有权限主机的命令。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| skip | int | 偏移量 (默认0) |
| limit | int | 每页数量 (默认50) |
| risk_level | string | 按风险等级筛选 (safe/warning/danger) |
| session_id | int | 按会话 ID 筛选 |
| keyword | string | 搜索命令关键词 |

**响应**：

```json
{
  "total": 500,
  "items": [
    {
      "id": 1,
      "session_id": 10,
      "command": "ls -la",
      "risk_level": "safe",
      "is_blocked": false,
      "output_snippet": null,
      "executed_at": "2026-05-17T04:10:00+00:00"
    }
  ]
}
```

#### GET `/audit/login-logs` 🔑

获取平台登录日志。管理员查看全部，普通用户仅查看自己的。

**查询参数**：`skip` (默认0), `limit` (默认50), `user_id` (int), `keyword` (匹配用户名/IP)

**响应**：

```json
{
  "total": 200,
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "username": "admin",
      "login_ip": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "login_method": "password",
      "is_success": true,
      "fail_reason": null,
      "login_at": "2026-05-17T04:30:00+00:00"
    }
  ]
}
```

#### GET `/audit/risk-commands` 🔑

获取风险命令列表（仅 warning 和 danger 级别）。

**查询参数**：`skip` (默认0), `limit` (默认50), `keyword` (搜索命令)

**响应**：

```json
{
  "total": 30,
  "items": [...]
}
```

#### GET `/audit/export/commands` 🔑

导出命令审计数据。最多导出 10000 条记录。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| format | string | 导出格式 (json/csv，默认json) |
| risk_level | string | 按风险等级筛选 (safe/warning/danger) |

**响应 (json)**：

```json
{
  "format": "json",
  "count": 500,
  "data": [
    {
      "id": 1,
      "session_id": 10,
      "command": "ls -la",
      "risk_level": "safe",
      "is_blocked": false,
      "executed_at": "2026-05-17T05:00:00+00:00"
    }
  ]
}
```

**响应 (csv)**：

```json
{
  "format": "csv",
  "count": 500,
  "data": "id,session_id,command,risk_level,is_blocked,executed_at\n1,10,ls -la,safe,False,...\n"
}
```

**错误码**：`400` — 不支持的格式，仅支持 json 或 csv

#### GET `/audit/ssh-login-logs` 🔑

获取 SSH 登录日志（通过后台采集远程主机 `/var/log/auth.log` 等）。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| host_id | int | 按主机筛选 |
| user_id | int | 按用户筛选 |
| risk_level | string | 按风险等级筛选 (safe/warning/danger) |
| is_success | bool | 按是否成功筛选 |
| keyword | string | 搜索 (匹配用户名/IP/主机名) |
| hours | int | 时间范围 (默认24小时) |
| skip | int | 偏移量 (默认0) |
| limit | int | 每页数量 (默认50) |

**响应**：

```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "host_id": 1,
      "host_name": "web-server-01",
      "username": "root",
      "login_ip": "192.168.1.100",
      "login_port": 22,
      "auth_method": "password",
      "is_success": true,
      "fail_reason": null,
      "login_at": "2026-05-17T04:30:00+00:00",
      "logout_at": null,
      "duration_seconds": null,
      "risk_level": "safe",
      "is_new_ip": false,
      "is_brute_force": false,
      "geo_location": null
    }
  ]
}
```

#### GET `/audit/ssh-login-logs/analysis` 🔑

SSH 登录日志统计分析。

**查询参数**：`host_id` (int，可选), `hours` (默认24)

**响应** (`SSHLoginAnalysisSummary`)：

```json
{
  "total_logins": 1500,
  "failed_logins": 45,
  "unique_ips": 25,
  "unique_users": 8,
  "brute_force_attempts": 3,
  "new_ip_logins": 12,
  "top_source_ips": [
    {"ip": "192.168.1.100", "count": 200}
  ],
  "top_users": [
    {"username": "root", "count": 500}
  ],
  "hourly_trend": [
    {"hour": "2026-05-17 00:00", "count": 50}
  ],
  "risk_distribution": [
    {"level": "safe", "count": 1400},
    {"level": "warning", "count": 55},
    {"level": "danger", "count": 45}
  ]
}
```

#### POST `/audit/ssh-login-logs/collect` 👑

手动触发 SSH 登录日志采集（仅管理员）。

**查询参数**：`host_id` (int，可选，不传则采集所有主机)

**响应**：

```json
{
  "message": "Collected 15 new SSH login records",
  "count": 15
}
```

---

### 11. SFTP 文件管理模块 (`/sftp`)

所有 SFTP 操作基于已注册主机的 SSH 连接，每次操作建立临时连接后关闭。

#### GET `/sftp/{host_id}/list` 🔑

列出远程目录文件。目录在前，文件在后，按名称排序。

**路径参数**：`host_id` (int)

**查询参数**：`path` (默认"/")

**响应** (`ListResponse`)：

```json
{
  "path": "/home",
  "files": [
    {
      "name": "..",
      "path": "/home/..",
      "is_dir": true,
      "size": 4096,
      "permissions": "drwxr-xr-x",
      "owner": "",
      "group": "",
      "modified_at": "2026-05-17T04:30:00"
    },
    {
      "name": "user",
      "path": "/home/user",
      "is_dir": true,
      "size": 4096,
      "permissions": "drwxr-xr-x",
      "owner": "",
      "group": "",
      "modified_at": "2026-05-17T04:30:00"
    },
    {
      "name": "file.txt",
      "path": "/home/file.txt",
      "is_dir": false,
      "size": 1024,
      "permissions": "-rw-r--r--",
      "owner": "",
      "group": "",
      "modified_at": "2026-05-17T04:30:00"
    }
  ]
}
```

#### POST `/sftp/{host_id}/mkdir` 🔑

创建文件夹。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | ✅ | 父目录路径 |
| name | string | ✅ | 文件夹名 |

**响应**：`{"success": true, "path": "/home/newdir"}`

#### POST `/sftp/{host_id}/rename` 🔑

重命名文件/文件夹。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | ✅ | 原路径 |
| new_name | string | ✅ | 新名称 |

**响应**：`{"success": true, "old_path": "/home/old", "new_path": "/home/new"}`

#### POST `/sftp/{host_id}/move` 🔑

移动文件/文件夹。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source_path | string | ✅ | 源路径 |
| target_path | string | ✅ | 目标目录路径 |

**响应**：`{"success": true, "source": "/home/file.txt", "target": "/tmp/file.txt"}`

#### POST `/sftp/{host_id}/copy` 🔑

复制文件/文件夹（使用 `cp -r`，支持递归复制目录）。

**请求体**：同 Move

**响应**：`{"success": true, "source": "...", "target": "..."}`

**错误码**：`400` — 复制失败

#### POST `/sftp/{host_id}/delete` 🔑

删除文件/文件夹（文件夹递归删除）。

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | ✅ | 要删除的路径 |

**响应**：`{"success": true, "path": "/home/file.txt"}`

#### GET `/sftp/{host_id}/download` 🔑

下载文件（流式响应）。不支持下载目录。

**查询参数**：`path` (必填，文件路径)

**响应**：文件流 (application/octet-stream)，包含 `Content-Disposition` 和 `Content-Length` 头

**错误码**：
- `400` — 不能下载目录
- `404` — 文件不存在

#### POST `/sftp/{host_id}/upload` 🔑

上传文件（multipart/form-data）。

**查询参数**：`path` (默认"/"，目标目录)

**请求体**：`files` (multipart 文件列表，支持多文件上传)

**响应** (`UploadResponse`)：

```json
{
  "success": true,
  "path": "/home/uploaded.txt",
  "name": "uploaded.txt",
  "size": 1024
}
```

#### GET `/sftp/{host_id}/exists` 🔑

检查路径是否存在。

**查询参数**：`path` (必填)

**响应**：

```json
// 存在时
{"exists": true, "is_dir": false, "size": 1024}

// 不存在时
{"exists": false}
```

---

### 12. 站点配置模块 (`/site-config`)

#### GET `/site-config/registration-status` 🔓

获取注册开放状态（公开接口，前端注册页使用）。

**响应**：

```json
{
  "allow_register": true
}
```

#### GET `/site-config` 👑

获取所有站点配置（仅管理员）。

**响应**：`list[SiteConfigResponse]`

```json
[
  {
    "id": 1,
    "key": "allow_register",
    "value": "true",
    "description": "Whether open registration is allowed",
    "updated_at": "2026-05-17T00:00:00+00:00"
  }
]
```

#### PUT `/site-config/{key}` 👑

更新单个站点配置。

**路径参数**：`key` (string，配置键名)

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| value | string | ❌ | 配置值 |
| description | string | ❌ | 配置说明 |

**响应**：`SiteConfigResponse`

**错误码**：`404` — 配置键不存在

#### POST `/site-config/batch` 👑

批量更新站点配置。若键不存在则自动创建。

**请求体**：`list[SiteConfigItem]`

```json
[
  {"key": "allow_register", "value": "false", "description": "关闭注册"}
]
```

**响应**：`list[SiteConfigResponse]`

---

## License

MIT License
