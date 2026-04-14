# 深圳 AI Agent MVP

这是一个可直接启动的演示项目，目标不是一次做成“大而全平台”，而是先把最容易成交的两个样板跑起来：

1. **外贸/跨境询盘转单 Agent**
2. **产品资料 / 工厂知识库销售助手**

这两个模块共用一套基础设施：

- FastAPI API 与演示前端
- SQLite 数据库
- 文档入库与切块
- 检索层（MVP 用 BM25，无需向量库）
- OpenAI 兼容 LLM 接口（DeepSeek / 通义千问 / OpenAI 都能挂）
- Mock 模式（没有 API Key 也能演示）

---

## 一、为什么先做这两个

### 1）询盘转单 Agent
MVP 可先覆盖：

- 邮箱转发到 webhook
- 官网表单直连 API
- 网站聊天系统 webhook
- 后续再接企业微信 / 飞书

自动完成：

- 询盘打分
- 提取型号、数量、认证、目的市场
- 生成英文首轮回复
- 给销售建议下一步动作

### 2）产品资料 / 工厂知识库销售助手
MVP 可先覆盖：

- 产品手册
- 规格书
- FAQ
- 认证文件
- 报价规则
- 售后政策

让销售、客服、老板都能先问起来。

---

## 二、项目结构

```text
shenzhen_agent_mvp/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── services/
│   │   ├── chunking.py
│   │   ├── document_parser.py
│   │   ├── retrieval.py
│   │   ├── llm.py
│   │   ├── heuristics.py
│   │   ├── lead_agent.py
│   │   └── kb_agent.py
│   ├── static/style.css
│   └── templates/index.html
├── sample_data/
│   ├── smart_lock_catalog.md
│   ├── faq_and_policy.md
│   └── certification_notes.md
├── .env.example
├── requirements.txt
├── Dockerfile
└── README_CN.md
```

---

## 三、本地启动

### 方式 A：最简单启动

```bash
cd shenzhen_agent_mvp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

打开：

```text
http://127.0.0.1:8000
```

### 方式 B：Docker 启动

```bash
docker build -t shenzhen-agent-mvp .
docker run --rm -p 8000:8000 shenzhen-agent-mvp
```

---

## 四、如何切到真实模型

默认 `.env.example` 里是：

```env
USE_MOCK_LLM=true
```

这意味着：

- 没有 API Key 也可以跑
- 可以先演示整个流程
- 但回答和打分是规则版，不是真实大模型版

### 1）接 DeepSeek

```env
USE_MOCK_LLM=false
LLM_API_KEY=你的_key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 2）接通义千问（百炼 OpenAI 兼容接口）

```env
USE_MOCK_LLM=false
LLM_API_KEY=你的_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-turbo
```

也可以把模型改成 `qwen-plus`。

### 3）接 OpenAI

```env
USE_MOCK_LLM=false
LLM_API_KEY=你的_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5.4-mini
```

---

## 五、推荐部署策略

### 第 1 阶段：你一个人就能卖

只卖两件事：

- 官网 / 邮件询盘自动分拣 + 首轮英文回复
- 工厂资料知识库问答

交付边界：

- 不碰 ERP / MES / 深度 CRM 改造
- 不承诺全自动报价
- 不承诺全自动客服闭环

### 第 2 阶段：第一批客户之后加功能

按顺序扩展：

1. 邮件转发自动入库
2. 企业微信 / 飞书 webhook
3. 销售任务看板
4. RFQ / BOM 解析
5. 报价草稿生成

---

## 六、演示方式

1. 先点击“加载内置 Demo 文档”
2. 提交一条英文询盘
3. 展示系统自动：
   - Lead Score
   - Lead Grade
   - 缺失字段
   - 建议动作
   - 英文首轮回复
4. 再让客户问：
   - MOQ 是多少？
   - 有哪些认证？
   - 交期多久？
   - 质保多久？

这套演示非常适合深圳的外贸老板、业务负责人、工厂老板。

---

## 七、下一步怎么做成可收费版本

### 标准版（最快成交）

- 1 个入口：官网表单 / 邮件 / 网站聊天 三选一
- 1 个知识库
- 1 个销售负责人通知
- 1 套英文回复模板

### 专业版

- 多渠道接入
- 多产品线知识库
- 多业务员分配
- 线索标签与统计报表
- 跟进 SLA

### 定制版

- 接 CRM / ERP
- 接企业微信 / 飞书 / Shopify / 独立站
- 报价审批流
- 客户画像与复购提醒

