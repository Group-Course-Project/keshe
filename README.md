# 西安中考志愿智能分析推荐系统

面向西安市初中毕业生及家长的志愿填报 Web 应用：以历年录取位次数据为知识库，通过「考生画像 + 冲稳保匹配 + 大模型分析报告」三步，把志愿填报变成有数据、有依据、可解释的决策辅助。

> 本项目结果仅供志愿参考，正式填报请以教育部门官方发布为准。

## 功能

- 智能推荐：根据预估位次、目标城区、住宿要求、公办/民办偏好，生成冲 / 稳 / 保三档候选学校。
- 位次趋势：ECharts 展示目标学校历年录取位次变化。
- AI 分析报告：调用大模型把结构化结果转成家长/考生能读懂的填报建议，无 API Key 时自动降级为规则模板。
- 模拟志愿：排列志愿顺序并校验梯度，降低滑档风险。
- 回测校准：用历史数据回测各档命中率，并给出推荐阈值组合。
- 特长生查询：按体育 / 艺术方向查询开设学校。

## 技术栈

- 前端：React 18 + TypeScript + Vite + Ant Design 5 + TanStack Query + ECharts
- 后端：Python + FastAPI + SQLAlchemy 2.0 + Pydantic
- 数据库：SQLite（开发环境）
- 大模型：DeepSeek（OpenAI 兼容协议，可选）

## 目录结构

```text
.
├── backend/          # FastAPI 后端
│   ├── app/          # 应用代码与业务服务
│   ├── .env          # 本地环境变量（含密钥，不入库）
│   ├── .env.example  # 环境变量模板
│   └── requirements.txt
├── frontend/         # React + Vite 前端
├── data/             # 原始 PDF、处理后 CSV 与 SQLite 数据库
├── docs/             # 项目方案文档
└── scripts/          # 数据清洗脚本
```

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
# Windows 激活：.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # 填入你的 DEEPSEEK_API_KEY，可留空使用降级模板
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`。

## 环境变量

在 `backend/.env` 中配置，参考 `backend/.env.example`：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，留空则使用规则降级模板 | 空 |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |

## 免责声明

推荐结果基于历史投档位次估算，位次会波动、政策会调整，仅供参考。请核对当年官方文件，并在官方平台自主填报。
