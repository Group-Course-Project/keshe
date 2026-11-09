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
- **账号体系**：注册 / 登录 / 登出，PBKDF2 加盐哈希存密码，服务端会话令牌；不登录仍可按匿名方式使用全部原有功能。
- **多套志愿方案**：把画像、志愿顺序与梯度结果存成快照，支持重命名、删除、载入回推荐页，勾选 2–3 套并排对比。
- **学校对比**：最多 4 所学校并排比较城区、性质、住宿、多年中位位次、数据质量与特长项目，附多系列位次走势图。
- **导出与分享**：志愿表一键导出 PNG 图片、通过打印视图导出 PDF；方案可生成免登录只读分享链接，随时撤销。
- **外部数据知识库**：2020–2025 逐年逐校录取线、历年控制线、2025 一分一段表、官方招生计划与学校档案，全部标注来源与可信等级；AI 报告会自动引用候选学校的收费 / 食宿 / 招生计划 / 特色信息。
- **校名归一（58 校口径）**：系统只收录原有 58 所有完整历年录取位次的学校；`school_aliases.csv` 保留 2 条主库学校的异写映射，供资料检索归一。
- **学校档案库 / 详情页**：58 所学校可搜索；详情页按「有数据才显示」分区展示历年位次、录取线（按满分制分表）、官方招生计划、特长生项目、校园档案与数据来源，缺失区块集中说明原因。

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
│   ├── requirements.txt
│   └── app/migrate.py  # 启动时自动建新表 / 给旧表补列
├── frontend/         # React + Vite 前端
├── data/
│   ├── raw/          # 官方招生计划 PDF、网页原始快照、图片表格转录件
│   ├── processed/    # 项目原有 58 校 / 348 条位次 CSV
│   ├── knowledge/    # 结构化知识库 CSV + school_aliases.csv 人工校名归一表（入库，可复现）
│   └── app.db        # SQLite（不入库）
├── docs/             # 项目方案 + 《西安中考数据知识库》.md / .pdf
└── scripts/          # 数据清洗、知识库构建、一键启动、冒烟测试脚本
```

## 快速开始

> **首次启动必读**：`data/app.db`（SQLite）被 `.gitignore` 忽略，仓库不含数据库。
> 直接启动后端再访问页面会因表不存在而报错，必须先执行下面的「初始化数据库」。

### 一键启动（Windows）

双击 `scripts/start_dev.bat`：自动创建虚拟环境、安装依赖、生成 `.env`、初始化数据库，并拉起前后端两个命令行窗口。
前端 `http://127.0.0.1:5173`，后端接口文档 `http://127.0.0.1:8000/docs`。

### 后端

```bash
cd backend
python -m venv .venv
# Windows 用 .venv\Scripts\python.exe，macOS / Linux 用 .venv/bin/python
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env    # Windows；macOS / Linux 用 cp。API Key 留空也能完整演示

# 首次必做：从 CSV / PDF 生成 data/app.db
.venv\Scripts\python.exe -c "from app.import_data import run; run()"     # 58 校 + 348 条位次
.venv\Scripts\python.exe -c "from app.import_talent import run; run()"   # 193 条特长生项目

# 导入外部采集知识库（幂等，可重复执行）
.venv\Scripts\python.exe -m app.import_knowledge

# 应用人工校名归一映射，把知识库中的新学校补进 school 表（幂等，必须放在 import_data 之后）
.venv\Scripts\python.exe -m app.import_schools_extended

.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

`start_dev.bat` 已内置上述全部导入步骤，一键启动时无需手动执行。
注意顺序：`import_data` 会 **delete + 重建 school 表**（主键会变），所以 `import_schools_extended` 必须在其之后运行；该脚本每次都会按标准校名重新回填 `school_alias.school_id`，因此重复执行安全。

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`。演示时「预估位次」建议填 **12000** 左右，可完整看到冲 / 稳 / 保三档；位次过低（如 500）冲稳两档为空，过高（如 25000）保档为空，属于当前数据分布所致。

本地已预置演示账号 **`demo` / `demo123456`**，内含两套方案，登录后可直接在「我的方案」里体验并排对比、分享与导出。也可以自己注册新账号验证数据隔离。

### 数据库升级（v0.3 起自动完成）

后端启动时通过 `app/migrate.py` 自动执行：`create_all()` 建新表（含 v0.3 账号/方案表、v0.4 知识库 6 表、v0.5 `school_alias`），再用 `PRAGMA table_info` 检查并 `ALTER TABLE ADD COLUMN` 给旧表补列（`candidate_profile.user_id`、`analysis_report.user_id`，以及 v0.5 的 `school.data_completeness` / `school.source_summary`）。**无需删库重跑导入脚本**，原有学校、位次、历史报告都会保留。若是全新环境，仍需按上面的「初始化数据库」步骤导入 CSV / PDF。

### 冒烟测试

后端启动后执行，覆盖注册登录、跨账号隔离、方案 CRUD、分享开关、学校对比与原有接口回归（每次用带时间戳的临时账号，不污染固定数据）：

```bash
cd backend
.venv\Scripts\python.exe ../scripts/smoke_test.py
```

## v0.3 升级说明（账号 · 方案 · 对比 · 导出 · 分享）

### 页面与入口

| 路径 | 说明 |
| --- | --- |
| `/` | 智能推荐：新增「保存为方案 / 导出图片 / 导出 PDF」，支持从方案「载入」恢复画像与志愿表 |
| `/compare` | 学校对比：最多 4 所，属性表 + 多年中位位次 + 多系列走势图 |
| `/plans` | 我的方案：列表、勾选 2–3 套并排对比、重命名、删除、分享、载入、导出 |
| `/share/:token` | 免登录只读分享页，可导出；链接撤销后立即失效 |
| `/reports` `/backtest` `/talents` | 原有页面，报告按账号隔离 |

### 认证与数据隔离

- 密码用 `hashlib.pbkdf2_hmac('sha256', …, 120000)` + 每账号随机盐，格式 `pbkdf2_sha256$迭代$salt$digest`；**不存明文**，不引入新依赖。
- 登录后返回随机 token 存 `auth_session` 表（30 天有效），前端放 `localStorage` 并由 axios 拦截器统一加 `Authorization: Bearer`，登出即服务端删除。
- 登录是**可选**的：未登录仍可用推荐、报告、回测、特长生、学校对比；只有方案保存 / 分享 / 列表需要登录。
- 画像与报告带可空 `user_id`。登录用户只看自己的报告，未登录只看历史匿名报告；方案与报告详情都做归属校验，跨账号返回 403。

### 数据表与接口

新增 3 张表：`app_user`、`auth_session`、`volunteer_plan`；`candidate_profile` / `analysis_report` 各补一个可空 `user_id` 列（由 `migrate.py` 自动迁移）。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/auth/register` `/auth/login` `/auth/logout` | 注册 / 登录 / 登出 |
| GET | `/auth/me` | 当前用户（未登录返回 `user: null`） |
| GET/POST | `/plans` | 方案列表 / 新建 |
| GET/PUT/DELETE | `/plans/{id}` | 详情 / 更新 / 删除 |
| POST/DELETE | `/plans/{id}/share` | 生成 / 撤销分享令牌 |
| GET | `/share/{token}` | 免登录只读方案快照 |
| POST | `/schools/compare` | 多校聚合对比数据 |

顺带修复：`POST /report` 不再重复写入 `recommendation_result`（原先同一画像会产生两批重复候选记录）。

### 为什么导出不用 html2canvas / jsPDF

两者都需要新增 npm 依赖，而本项目 `node_modules` 曾因镜像超时下载不完整。这里用浏览器原生能力实现，零依赖、结果稳定：

- **PNG**：Canvas 2D 直接绘制卡片，中文由系统字体渲染，`toBlob` 下载。
- **PDF**：新窗口生成带 `@media print` 的打印视图并调用 `window.print()`，在浏览器打印对话框选「另存为 PDF」。长表格不会被截断。

### 已知边界

- 分享链接是 SPA 路由，部署到静态服务器时需配置 history fallback（Vite dev / preview 已内置）。
- 方案保存的是**快照**，不随推荐算法或数据更新自动重算。
- 令牌存 `localStorage`、CORS 仍为 `*`、分享链接为无鉴权只读——这是课程设计的本地演示取向，生产环境需换成 HttpOnly Cookie、收敛域名并给分享链接加有效期 / 访问限制。

## v0.4 数据采集与知识库（2026-11-08）

### 交付内容

| 数据 | 规模 | 说明 |
| --- | --- | --- |
| 逐校录取线 | 270 条 / 58 校 / 2020–2025 | 统招线、定转统线、得分率、来源与可信等级 |
| 录取控制线 | 6 个年度 | 普高线、体艺特长生线、综合高中班线 |
| 一分一段表 | 159 档（2025 城六区） | 分数 → 累计位次，可用于「按成绩填」入口 |
| 官方招生计划 | 57 校 | 计划总数、统招 / 定向 / 特长生人数、特色班与特长项目 |
| 学校档案 | 9 所 | 地址、招生代码、官网、电话、学费、住宿费、食宿、办学特色 |
| 学校名录 | 58 校 | 学校属性 / 办学性质 / 招生批次 |

人工可读、可直接投喂给大模型的完整文档：**`docs/西安中考数据知识库.md`** 与 **`docs/西安中考数据知识库.pdf`**（同源生成，可直接打印）。原始网页快照与图片表格转录件保存在 `data/raw/web/`，15 个数据源的 URL、类型与可信等级见 `data/knowledge/data_sources.csv`。

### 必读的两条口径

1. **西安市教育局每年只公布「录取最低控制线」，不逐校公布城六区各高中录取线**（受「十项严禁」约束）。因此本项目的逐校录取线**全部是第三方汇总数据（C/D 级）**，不是官方数据，答辩与界面文案都不能这么表述。
2. **总分口径变过三次**：2020–2024 为 700 分制，2025 改为 820 分制，2026 起改为 640 分制。**跨年分数绝对不能直接连成趋势线**，请用 `得分率` 列或一分一段表换算位次。

可信等级：`A` 教育部门/学校官网正式文件、`B` 主流媒体刊登的学校署名简章、`C` 第三方汇总（原表自述非官方）、`D` OCR 转录仅作背景参考。

### 复现与导入

```bash
# 1) 清洗：从 data/raw/web/ 快照 + 官方 PDF + 种源数据生成 data/knowledge/*.csv
python scripts/build_knowledge_dataset.py       # 需 pdfplumber（已在 requirements.txt）

# 2) 生成投喂文档（Markdown + PDF，PDF 由本机 Chrome/Edge 无头打印，零额外依赖）
python scripts/build_knowledge_doc.py

# 3) 导入数据库（幂等）
cd backend && .venv\Scripts\python.exe -m app.import_knowledge
```

### 新增表与只读接口

新增 6 张独立表：`control_line`、`admission_score`、`score_rank_map`、`enrollment_plan`、`school_profile`、`data_source`。**不改动** `school` / `enrollment_record` / `school_talent`，冲稳保推荐结果完全不受影响；`migrate.py` 启动时自动建表。

| 路径 | 用途 |
| --- | --- |
| GET `/knowledge/summary` | 各表数据量与免责声明 |
| GET `/knowledge/control-lines` | 历年控制线 |
| GET `/knowledge/admission-lines?school=&year=` | 逐校逐年录取线 |
| GET `/knowledge/score-to-rank?score=700` | 分数 → 城六区累计位次（无精确档取最近下一档） |
| GET `/knowledge/school?name=` | 聚合档案 + 官方计划 + 历年线 |
| GET `/knowledge/sources` | 数据源清单 |

`POST /report` 现在会把候选学校的收费、食宿、招生计划、特长项目与办学特色拼成上下文注入 Prompt（最多 8 所），并在 system 提示中约束「只能引用明确写出的信息，不得推断」。无 Key 的降级模板也会追加「学校补充信息」章节。知识库为空时行为与升级前一致。

### 顺带发现的原有数据问题（未擅自改动）

- `scripts/clean_data.py` 中 `是否住宿` 是 `random.randint(0,1)` **随机生成**的，不是真实数据；本次只补充了 9 所学校的真实食宿描述，其余仍应视为「未知」而非随机布尔值。
- `backend/app/import_talent.py` 对**民办 PDF 只有 14 列**却读取 `row[15]/row[16]`，导致民办校特长项目从未导入。新管线按公办 18 列 / 民办 14 列分别解析，收敛后保留 50 所含特长项目的招生计划，可据此修正。
- 陕师大附中招生简章写「拟招 651 人」，教育局官方 PDF 为 596 人——以官方 PDF 为准，说明多源交叉校验的必要性。

## v0.5 校名归一（已收敛为 58 校口径）

### 当前口径

**系统只收录原有 58 所有完整历年录取位次的学校**，`school` 表 58 行全部为 `data_completeness=full`，均可参与冲稳保推荐。

历史上曾把外部知识库中 61 所「只有录取线 / 招生计划 / 校园档案、没有位次」的学校补进 `school` 表（当时共 119 所）。2026-11-09 按需求删除：这 61 所学校记录、其对应的 158 条录取线 / 59 条招生计划 / 4 份校园档案、以及 70 条指向它们的别名映射，均已从数据库与 CSV 源同步移除，并切断了启动脚本的重建链路。历史判断依据保留在 git 提交 `c9d54da` 与本地备份中，不再参与系统运行。

当前 `data/knowledge/school_aliases.csv` 只保留 2 条**主库已有校**的异写映射（「西安89中」→ 西安市第八十九中学；「西安市铁一中国际合作学校」→ 西安铁一中国际合作学校），落库为 `school_alias` 表，可通过 `GET /school-aliases` 审计。知识库对这 58 校的资料增强（录取线、控制线、一分一段、招生计划、校园档案、AI 报告上下文）全部保留。

### 数据完整度与「不臆造」原则

`school` 表新增 `data_completeness`（`full` / `knowledge_only` / `profile_only`）与 `source_summary` 两列，由 `migrate.py` 自动补列，旧库默认 `full`。

- **推荐结果不变**：`recommend()` 显式跳过非 `full` 学校；当前 58 校全部为 `full`，实测 12000 位次仍为冲 5 / 稳 5 / 保 8。
- `has_dormitory` 仍由 `clean_data.py` 的 `random.randint` 生成，不是真实数据；详情页对这 58 校标注「未核实·随机占位值不可作为择校依据」。
- 详情页只返回实际采集到的字段，未采集区块集中说明原因，不臆造数据。

### 接口与前端

| 变更 | 说明 |
| --- | --- |
| `GET /schools`、`POST /schools/compare` | 新增 `data_completeness` / `source_summary` / `has_rank_data`；对比接口在无位次学校参与时追加提示 |
| `GET /knowledge/school?name=` | 支持任意已归一别名，合并同一学校分散在不同写法下的档案 / 计划 / 录取线，返回 `canonical_name` 与 `aliases` |
| `GET /school-aliases` | 只读返回全部映射与判断依据 |
| AI 报告上下文 | 按别名展开后再匹配，例如「西安铁一中国际合作学校」现在能取到写作「西安市铁一中国际合作学校」的招生计划 |
| 前端 | 对比页保留「数据完整度 / 资料来源」两行；当前 58 校全部有位次，推荐页知识库概况显示 58 所可推荐 |

### 已知边界

- 系统只覆盖 58 所有历年位次的学校；外部资料（录取线 / 招生计划 / 校园档案）仅用于查询与 AI 报告上下文，不能据此估算位次。若未来要扩库，需先补齐可溯源的同口径位次数据（不是用分数反推）。

## v0.6 学校档案库与渐进式详情页

### 做法

新增 `GET /schools/{school_id}/detail`：按 `school_alias` 展开该校全部写法后，一次聚合 6 张表（位次 / 逐校录取线 / 官方招生计划 / 特长生 / 校园档案 / 数据源），每个区块独立返回 `available` 与缺失 `reason`。前端只渲染有数据的区块，缺失项集中到「尚未采集的资料」卡片，因此 58 所学校点开都有内容且不会露出假数据。

前端新增「学校档案」入口：`/schools` 为可搜索可筛选的列表页，`/schools/:id` 为详情页；学校对比表头、推荐候选操作列、特长生查询结果均加了跳转链接。

### 数据诚实性处理

- **住宿字段**：58 所学校的 `has_dormitory` 由 `clean_data.py` 随机生成，详情页显示值后标注「未核实」并说明「随机占位值，不可作为择校依据」。
- **跨分值制**：录取线按 `full_score` 分组为 700 分制（2020–2024）/ 820 分制（2025）两张表，禁止混画趋势；D 级 OCR 转录数据额外弹出低可信度提示。
- **校园档案**：只返回 10 个字段中实际采集到的值，并写明「本校采集到 n 个」，未列出的字段不代表学校不提供。
- **别名与来源**：页面展示该校别名，底部按数据源列出可信等级与原始链接。

### 验证

冒烟测试共 42 项全部通过（含全量 58 所详情接口回归）；`tsc` 零错误、`vite build` 通过。
- `start_dev.bat` 只重建 58 校主库与知识库（6 张知识表按 CSV 幂等重建），**不会**再补录学校；`import_schools_extended.py` 与 `build_knowledge_dataset.py` 均已停用并内置防误跑保护。
- 统计口径可随时复算：`backend/.venv/Scripts/python.exe scripts/analyze_school_coverage.py`（该脚本的启发式归一含已知误判，且输出为历史 119 校时期的估算口径，仅作审计参考；正式口径以 `school_aliases.csv` 与 58 校主库为准）。

### v0.7 收敛为 58 校（2026-11-09）

按需求删除扩展期补录的 61 所仅资料学校：`school` 表回到 58 所，知识库同步收敛为 270 条录取线 / 57 校招生计划 / 9 份校园档案 / 2 条别名；前端页面全部保留，仅说明文案改为 58 校口径。原始数据备份在 `C:/Users/LENOVO/AppData/Local/Temp/keshe_backup_58_20261109/`，历史完整版本见 git 提交 `c9d54da`。

### v0.8 特长生查询增强 · 住宿模拟值显式化（2026-11-09）

- 导航顺序调整为「智能推荐 → 特长生查询 → 学校档案 → …」。
- **住宿字段明确为模拟数据**：`scripts/generate_dormitory_mock.py` 独立生成 0/1（默认 `seed=42` 可复现，`--seed` / `--random-seed` 可换一批），同时写回 `data/processed/schools.csv` 与 `data/app.db`；`clean_data.py` 不再隐式随机，只写占位 0；`start_dev.bat` 每次启动调用一次，重建数据库也不会丢。详情页、对比页、特长生页、推荐页筛选项全部标注「模拟数据，不可作为择校依据」。
- **特长生查询**：新增逐年文化课控制线（6 年、含来源等级，2020/2021 明确标注无可靠来源）与分数过线自查；结果表补 2025 官方招生名额（≤2 人标「名额极少」）、特色班；支持不选项目查全部、多选项目「任一命中 / 同时开设全部」两种匹配；可勾选最多 4 所跳转对比页预选，或一键加入「我的方案」。
- 数据来源页的本地 PDF 原件改为只读端点 `GET /source-files/{filename}` 提供（拒绝路径穿越/非 PDF），不再被 SPA 兜底跳回首页；修正招生计划中 OCR 错字「乓乓球」→「乒乓球」。

## 环境变量

在 `backend/.env` 中配置，参考 `backend/.env.example`：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，留空则使用规则降级模板 | 空 |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |

## 免责声明

推荐结果基于历史投档位次估算，位次会波动、政策会调整，仅供参考。请核对当年官方文件，并在官方平台自主填报。

外部采集数据仅用于课程设计学习，均来自公开网页，未采集个人信息。逐校录取线为第三方汇总（非官方发布），学费、招生计划随年度政策调整，详见 `docs/西安中考数据知识库.md` 第 1 节与第 10 节。
