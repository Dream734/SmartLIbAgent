# 图书馆选座与图书预借系统

一个基于 **FastAPI + Vue 3** 的图书馆业务系统，支持座位预约、图书预借、管理员审批，以及基于 LangGraph 的 AI 智能预约助手和知识库检索。

## 功能特性

- 座位管理：区域/座位增删改查，整点、半点预约，单次最长 4 小时。
- 座位预约：申请 → 管理员审批 → 预约/取消/离座，冲突时段自动拦截，超时未审批自动取消。
- 图书预借：分类/图书管理、封面上传、预借保留 2 天、审批与借阅状态流转。
- 用户管理：注册登录、JWT 鉴权、管理员增删改查用户、修改密码。
- AI 智能助手：LangGraph Agent 查询座位/图书/我的预约，并支持两阶段确认预约与预借。
- 知识库 RAG：读取 `backend/data/db/*.md` 规则文档，通过 Ollama 向量模型检索。

## 技术栈

- 后端：FastAPI、SQLAlchemy 2、PyMySQL、PyJWT、bcrypt、LangGraph、LangChain、ChromaDB
- 前端：Vue 3、Vite、Vue Router、Element Plus、Axios、marked + DOMPurify
- 数据库：MySQL
- 本地模型：Ollama（`qwen2.5:7b` 用于对话/工具调用，`bge-m3` 用于向量化）

## 目录结构

```text
lab-agent/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── common/       # 统一响应、异常处理
│   │   ├── dependencies/ # 登录鉴权依赖
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── services/     # 业务逻辑与 Agent
│   │   └── utils/        # JWT、密码等工具
│   ├── data/db/          # 知识库 .md 文档
│   ├── uploads/          # 运行时上传文件
│   ├── .env.example
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api/          # 前端接口封装
        ├── layouts/      # 页面布局
        ├── router/       # 路由与守卫
        ├── utils/        # 请求、鉴权等工具
        └── views/        # 页面
```

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 22.18+（推荐 24.x）
- MySQL 8+
- Ollama（可选，AI 助手和知识库需要）

### 1. 创建数据库

在 MySQL 中创建项目数据库，应用启动时会自动创建数据表：

```sql
CREATE DATABASE lab_agent DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 启动后端

```powershell
cd backend
copy .env.example .env
```

编辑 `.env`，至少配置 `DATABASE_URL` 和 `JWT_SECRET_KEY`：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/lab_agent
JWT_SECRET_KEY=请替换为随机密钥
```

安装依赖并启动：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端默认运行在 `http://127.0.0.1:8000`，接口文档见 `http://127.0.0.1:8000/docs`。

### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`。开发环境下 Vite 会把 `/api` 和 `/uploads` 代理到 `http://127.0.0.1:8000`。

## 环境变量

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `DATABASE_URL` | MySQL 连接串 | `mysql+pymysql://root:123456@127.0.0.1:3306/lab_agent` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | 随机字符串 |
| `JWT_EXPIRE_HOURS` | Token 有效小时数 | `24` |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `CORS_ORIGINS` | 允许的前端源，多个用英文逗号分隔 | `http://127.0.0.1:5173,http://localhost:5173` |
| `LLM_API_KEY` | OpenAI 兼容接口的 API Key | `ollama` |
| `LLM_BASE_URL` | LLM 接口地址 | `http://127.0.0.1:11434/v1` |
| `LLM_MODEL` | 对话/工具调用模型 | `qwen2.5:7b` |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | 知识库向量模型 | `bge-m3` |

## AI 助手与知识库

1. 拉取本地模型：

```powershell
ollama pull qwen2.5:7b
ollama pull bge-m3
```

2. `.env` 中设置：

```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=bge-m3
```

3. 知识库文档放在 `backend/data/db/*.md`，首次检索时会向量化，稍慢属于正常现象。

> 注意：Agent 依赖 Function Calling，请使用支持 `tools` 的模型（如 `qwen2.5:7b`）。`deepseek-r1:7b` 只支持普通文本生成，不适合本项目的 Agent。

## 默认账号

项目不内置默认账号。注册的新账号默认角色为 `student`；需要管理员权限时，可将 `users` 表中对应记录的 `role` 改为 `admin`，或登录管理员后通过“用户管理”新增管理员。

## 常见问题

- **分页列表为空**：后端分页接口统一返回 `{"items": [...], "total": n}`，前后端字段名需保持一致。
- **上传文件不显示**：文件保存在 `backend/uploads/`，通过 `/uploads/...` 访问；该目录不应提交到 Git。
- **AI 助手 500**：先确认 Ollama 已启动，且 `LLM_MODEL` 支持工具调用。

