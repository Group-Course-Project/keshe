# -*- coding: utf-8 -*-
"""
从 data/knowledge/*.csv 生成「可投喂」知识库文档：Markdown + PDF（同源、可重复生成）。

用法：
  python scripts/build_knowledge_doc.py

输出：
  docs/西安中考数据知识库.md     —— 适合直接贴给大模型 / 进 RAG 知识库 / 给答辩老师看
  docs/西安中考数据知识库.pdf    —— 适合打印、归档、作为附件投喂
  docs/.build/knowledge.html     —— 中间产物（HTML 打印源）

PDF 由本机 Chrome/Edge 无头打印生成，不引入任何 Python 依赖。
"""
from __future__ import annotations

import csv
import html as html_mod
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "data" / "knowledge"
DOCS = ROOT / "docs"
BUILD = DOCS / ".build"
BUILD.mkdir(parents=True, exist_ok=True)


def read(name: str) -> list[dict]:
    with (K / name).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def md_table(header: list[str], rows: list[list[str]]) -> list[str]:
    def esc(v):
        return str(v or "").replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(esc(h) for h in header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return out


M: list[str] = []
def w(line: str = "") -> None:
    M.append(line)


summary = json.loads((K / "dataset_summary.json").read_text(encoding="utf-8"))
lines = read("admission_lines_2020_2025.csv")
controls = read("control_lines_2020_2025.csv")
ranks = read("score_rank_map_2025.csv")
plans = read("enrollment_plan_2025.csv")
profiles = read("school_profiles.csv")
sources = read("data_sources.csv")

# ---------------------------------------------------------------- 封面与导读
w("# 西安中考录取数据与高中校园信息知识库")
w()
w("> **覆盖年份**：2020–2025（近 5 个完整招生年度为 2021–2025）  ")
w("> **数据抓取日期**：2026-11-08  ")
w(f"> **逐校录取线**：{summary['逐校录取线记录']} 条 / {summary['覆盖学校数']} 所学校  ")
w(f"> **官方招生计划**：{summary['官方招生计划学校数']} 所（含 {summary['其中含特长生项目']} 所特长生项目）  ")
w(f"> **一分一段表**：{summary['一分一段分数档位数']} 个分数档位（2025 城六区）  ")
w(f"> **学校详细档案**：{summary['校园档案数']} 所  ")
w("> **用途**：课程设计项目「西安中考志愿智能分析推荐系统」的数据补充，可直接投喂给大模型或导入数据库。")
w()
w("---")
w()
w("## 0. 这份文档怎么「投喂」给项目")
w()
w("有三种用法，按需要选：")
w()
w("1. **作为大模型知识库（最直接）**：把本 Markdown 或 PDF 上传到资料库 / RAG 知识库，"
  "或修改 `backend/app/services/llm.py` 的 Prompt，把「学校档案」「历年控制线」「一分一段」作为上下文注入。"
  "AI 报告就能回答「某校学费多少」「我考 700 分大概多少名」这类原本答不了的问题。")
w("2. **作为结构化数据导入数据库**：`data/knowledge/*.csv` 每个字段都带 `来源ID` 与 `可信等级`，"
  "执行 `python -m app.import_knowledge` 即可写入新增表，不影响原有 58 校与推荐算法。")
w("3. **作为答辩/人工查阅资料**：PDF 可直接打印，含完整来源清单与免责声明。")
w()
w("配套文件清单：")
w()
w("| 文件 | 内容 |")
w("| --- | --- |")
w("| `data/knowledge/admission_lines_2020_2025.csv` | 逐年逐校统招线 / 定转统线 / 得分率 / 来源 |")
w("| `data/knowledge/control_lines_2020_2025.csv` | 历年普高线、特长生线、综合高中班线 |")
w("| `data/knowledge/score_rank_map_2025.csv` | 2025 分数 → 城六区累计位次（159 档） |")
w(f"| `data/knowledge/enrollment_plan_2025.csv` | 教育局官方招生计划与特长生项目（{summary['官方招生计划学校数']} 校） |")
w("| `data/knowledge/school_profiles.csv` | 校园档案：地址、学费、食宿、特色等 |")
w(f"| `data/knowledge/school_directory_extended.csv` | 学校名录（{summary['扩展学校名录']} 校，含属性/性质/批次） |")
w("| `data/knowledge/data_sources.csv` | 15 个数据源的 URL、类型与可信等级 |")
w("| `data/raw/web/` | 全部网页原始快照与图片表格转录件（可追溯） |")
w()

# ---------------------------------------------------------------- 口径与局限
w("---")
w()
w("## 1. 必读：数据口径与局限")
w()
w("### 1.1 官方并不逐校公布城六区录取分数线")
w()
w("这是本次调研最重要的结论。西安市教育局每年只公布**录取最低控制线**（普高线、体艺特长生线等），"
  "并依据教育部、省教育厅「十项严禁」明确**严禁宣传中高考成绩排名、升学率**，"
  "因此城六区各高中的逐校统招线/定转统线**没有统一的官方发布渠道**。")
w()
w("西安中考网在《2023年西安中考120所高中学校录取分数线汇总》中亦明确写道："
  "「因中考没有官方公开发布分数线的习惯，以下分数线统计均来自学校、家长、学生等汇总信息，仅供大家参考！」")
w()
w("本知识库中的逐校录取线因此**全部来自第三方汇总站或公众号整理**（可信等级 C/D），"
  "仅控制线（部分年份 A 级）、招生计划（A 级）、学校官网招生简章（A/B 级）属于一手来源。"
  "**请勿在答辩或产品界面中把逐校线表述为「官方数据」**。")
w()
w("### 1.2 总分口径变了三次，跨年分数绝对不能直接比较")
w()
w("| 年份 | 中考总分满分 | 城六区普高线 | 说明 |")
w("| --- | --- | --- | --- |")
w("| 2020 | 700 | 509 | 700 分制 |")
w("| 2021 | 700 | 496 | 700 分制 |")
w("| 2022 | 700 | 523 | 700 分制 |")
w("| 2023 | 700 | 539 | 700 分制 |")
w("| 2024 | 700 | 501.0 | 700 分制（试题难度变化，分数线明显回落） |")
w("| 2025 | **820** | 611.0 | 总分由 700 调整为 820，分值不可与往年直接比 |")
w("| 2026 起 | **640** | 待官方公布 | 新中考改革，满分再次调整 |")
w()
w("因此数据表中提供了 **得分率 = 统招线 ÷ 当年满分**，这才是跨年可比的口径；"
  "更严谨的做法是用「一分一段表」把分数换算成**位次**再比较——这也正是本项目推荐算法采用位次的原因。")
w()
w("### 1.3 位次口径")
w()
w("本知识库的一分一段表为**城六区（0198 招生单元）总分累计位次**。"
  "五区二县与西咸新区是独立招生单元，位次口径不同，不能混用。"
  "项目方案文档 §10 把「全市位次 / 分区位次」列为待确认问题，动手接入前必须先定死口径。")
w()
w("### 1.4 特长生是两条录取线")
w()
w("2025 年城六区普高线 611.0 分，体育/艺术特长生控制线仅 366.6 分，"
  "试点综合高中班 595.0 分。特长生按「专项测试 + 文化课过线」录取，"
  "**其位次参考意义很弱**，不应套用统招的冲稳保算法（见项目方案 §11）。")
w()
w("### 1.5 项目原有数据存在两个已知问题（本次一并记录）")
w()
w("1. `scripts/clean_data.py` 中 `是否住宿` 字段是 `random.randint(0,1)` **随机 mock** 生成的（脚本注释已写明"
  "「按用户要求随机 mock」），不是真实住宿信息。本知识库的 `school_profiles.csv` 提供了部分学校的真实食宿描述，"
  "但仍未覆盖全部 58 校。")
w("2. `data/processed/enrollment_records.csv` 的 348 条位次来自一个**未入库的本地表格**"
  "（`C:/Users/.../Downloads/表格_20261101.csv`），其中 22.4% 为「约 / 补录 / 无数据 / 区间」等非精确值，"
  "来源不可追溯。本知识库未覆盖它，也未替换它——两者口径独立。")
w()
w("### 1.6 可信等级定义")
w()
w("| 等级 | 含义 | 本库中的典型来源 |")
w("| --- | --- | --- |")
w("| A | 教育行政部门文件 / 学校官网正式发布 | 2025 招生计划 PDF、西安中学特长生简章、人民网转发的控制线 |")
w("| B | 主流媒体刊登的学校署名招生简章 | 三秦都市报中招特刊、华商报、西安新闻网、学校公众号 |")
w("| C | 第三方汇总站 / 公众号整理（原表自述非官方） | 2023–2025 三年汇总表、新时高考网、52中考网、一分一段表 |")
w("| D | OCR 转录、存在识别误差，仅作背景参考 | 2020–2021 分数线图片表格 |")
w()

# ---------------------------------------------------------------- 概览
w("---")
w()
w("## 2. 数据集概览")
w()
w("| 指标 | 数值 |")
w("| --- | --- |")
for k in ["逐校录取线记录", "覆盖学校数", "其中匹配项目现有学校库", "控制线年份数",
          "一分一段分数档位数", "官方招生计划学校数", "其中含特长生项目",
          "校园档案数", "扩展学校名录", "数据源数"]:
    w(f"| {k} | {summary[k]} |")
w()
w("各年份逐校录取线记录数：" + "、".join(
    f"{y} 年 {n} 条" for y, n in summary["各年份记录数"].items()) + "。")
w()
w("> **口径说明（2026-11-09）**：系统只保留原有 58 所有完整历年位次数据的学校。"
  "上表「覆盖学校数」为校名归一后的实体数；录取线表中另有 2 个历史异写"
  "（「西安89中」「西安市铁一中国际合作学校」），经 `school_aliases.csv` 归并到主库，"
  "58 校中有 1 所暂无逐校录取线记录。")
w()
w("> 注意：`官方A级记录数` 为 0 —— 这**不是抓取失败**，而是 1.1 节所述「官方不逐校公布」的直接体现。"
  "逐校线的价值在于趋势与相对位置，不能当作权威投档线。")
w()

# ---------------------------------------------------------------- 控制线
w("---")
w()
w("## 3. 历年城六区录取控制线")
w()
M.extend(md_table(
    ["年份", "满分", "普高线", "体艺特长生线", "综合高中班线", "来源", "等级", "备注"],
    [[r["年份"], r["总分满分"], r["普高录取控制线"], r["体艺特长生控制线"],
      r["综合高中班控制线"], r["来源ID"], r["可信等级"], r["备注"]] for r in controls]))
w()

# ---------------------------------------------------------------- 一分一段
w("---")
w()
w("## 4. 2025 一分一段表（分数 → 城六区累计位次）")
w()
w("用于把家长手里的**分数/估分**换算成系统需要的**位次**，这是项目 P0 升级点所缺的一层。"
  "例如 700 分 ≈ 城六区 27260 名；611 分（当年普高线）约对应 4.1 万名以后的位置。")
w()
w("完整 159 档如下（来源 S10，等级 C；802 分及以上为屏蔽段，官方延迟公布具体分数）：")
w()
M.extend(md_table(
    ["中考成绩", "城六区累计位次", "位比%"],
    [[r["中考成绩"], r["城六区累计位次"] or "屏蔽", r["位比%"]] for r in ranks]))
w()

# ---------------------------------------------------------------- 逐校线
w("---")
w()
w("## 5. 逐校录取线（2020–2025 统招线，单位：分）")
w()
w("**警告**：2025 为 820 分制，与 2020–2024 的 700 分制不可直接连成趋势线。"
  "跨年比较请使用 `data/knowledge/admission_lines_2020_2025.csv` 中的 `得分率` 列，或用一分一段表换算位次。")
w()
w("表中 `·` 表示该年无可靠数据；`匹配` 标记表示该校能与项目现有 `schools.csv` 的 58 所学校对齐。")
w()
by_school: dict[str, dict] = {}
for r in lines:
    key = r["标准校名"]
    by_school.setdefault(key, {})[r["年份"]] = r
rows = []
for name in sorted(by_school, key=lambda n: -float(by_school[n].get("2025", {}).get("统招线") or 0)):
    g = by_school[name]
    mark = "✓" if g.get("2025", g.get("2024", {})).get("匹配状态") == "匹配项目学校库" else ""
    rows.append([name + (" ✓" if mark else "")] + [g.get(str(y), {}).get("统招线") or "·" for y in range(2020, 2026)])
M.extend(md_table(["学校", "2020", "2021", "2022", "2023", "2024", "2025"], rows))
w()
w(f"共 {len(rows)} 个校名写法（其中 2 个为别名，归一后对应 58 所学校）。完整字段（定转统线、得分率、学校属性、办学性质、招生批次、"
  "来源ID、可信等级、交叉校验值、备注）见 `admission_lines_2020_2025.csv`。")
w()

# ---------------------------------------------------------------- 招生计划
w("---")
w()
w("## 6. 2025 年官方招生计划与特长生项目")
w()
w("来源：西安市教育局《2025年城六区公办/民办普通高中招生计划》PDF 原件（等级 A）。"
  "这是本次补数据里**唯一覆盖全量学校的一手官方材料**。")
w()
M.extend(md_table(
    ["学校", "性质", "计划总数", "统招", "定向", "体育类特长项目", "艺术类特长项目"],
    [[r["标准校名"], r["办学性质"], r["招生计划总数"], r["统招生计划"],
      r["定向生计划"], r["体育类特长项目"] or "·", r["艺术类特长项目"] or "·"] for r in plans]))
w()
w("> 工程提示：项目原有的 `backend/app/import_talent.py` 只取了 PDF 的 `row[15]/row[16]` 两列，"
  "但**民办表只有 14 列**，导致民办学校的特长生项目一直没导入。本知识库按公办 18 列 / 民办 14 列分别解析，"
  "共得到 96 所含特长项目的学校，可用于修正该问题。")
w()

# ---------------------------------------------------------------- 校园档案
w("---")
w()
w("## 7. 学校详细档案")
w()
w("以下信息来自学校署名招生简章或学校官网，**缺失字段一律留空、未作推测**。"
  "学费标准随年度政策变化，实际缴费以学校当年公示为准。")
w()
for p in profiles:
    w(f"### {p['标准校名']}")
    w()
    w(f"- **地址**：{p['学校地址'] or '未获取'}")
    w(f"- **招生代码**：{p['招生代码'] or '未获取'}　**官网**：{p['官网'] or '未获取'}　**电话**：{p['咨询电话'] or '未获取'}")
    w(f"- **学费**：{p['学费'] or '未获取'}")
    w(f"- **住宿费**：{p['住宿费'] or '未获取'}")
    w(f"- **食宿条件**：{p['食宿条件'] or '未获取'}")
    w(f"- **招生计划**：{p['2025招生计划'] or '未获取'}")
    w(f"- **特长生**：{p['特长生信息'] or '未获取'}")
    w(f"- **办学特色**：{p['办学特色/简介'] or '未获取'}")
    w(f"- **来源**（等级 {p['可信等级']}）：{p['来源URL']}")
    w()

# ---------------------------------------------------------------- 数据源
w("---")
w()
w("## 8. 数据源清单")
w()
M.extend(md_table(
    ["ID", "来源", "类型", "等级", "说明"],
    [[r["来源ID"], r["来源名称"], r["类型"], r["可信等级"], r["说明"]] for r in sources]))
w()
w("原始 URL 与本地快照路径见 `data/knowledge/data_sources.csv`；"
  "网页快照保存在 `data/raw/web/`，三秦都市报中招特刊 8 篇保存在 `data/raw/web/sanqin/`。")
w()

# ---------------------------------------------------------------- 接入说明
w("---")
w()
w("## 9. 接入项目的字段映射建议")
w()
w("| 项目现有表 / 字段 | 建议补入的数据 | 说明 |")
w("| --- | --- | --- |")
w("| `enrollment_record.min_score`（方案 §6 草案，当前未建） | `admission_lines` 的 `统招线` | 必须同时存 `总分满分` 或只用 `得分率`，否则跨年不可比 |")
w("| `enrollment_record.plan_count`（当前未建） | `enrollment_plan_2025` 的 `招生计划总数` | 官方 A 级数据 |")
w("| `enrollment_record.source_url`（当前未建） | `data_sources` 对应 URL | 满足方案 §8.1「版本可追溯」要求 |")
w("| `school.intro / official_site`（当前未建） | `school_profiles` | 学校详情页的数据基础 |")
w("| `school.has_dormitory`（当前为随机 mock） | `school_profiles.食宿条件` | 仅 13 校有真实描述，其余应改为「未知」而非随机值 |")
w("| 新表 `score_rank_map` | `score_rank_map_2025` | 支撑「分数 → 位次」入口（项目 P0 升级点） |")
w("| 新表 `control_line` | `control_lines` | 支撑特长生双线提示与线差展示 |")
w()
w("**迁移注意**：项目当前用 `Base.metadata.create_all()` 建表，它**不会给已存在的表加列**，"
  "且 `data/app.db` 被 gitignore 不入库。新增字段需走 `backend/app/migrate.py` 的 `ALTER TABLE` 逻辑"
  "（本次升级已引入自动迁移），否则会出现「本机正常、别人 clone 后报表不存在」。")
w()

# ---------------------------------------------------------------- 免责
w("---")
w()
w("## 10. 免责声明")
w()
w("1. 本数据集为**课程设计学习用途**，采集自公开网页，未采集任何个人信息，未绕过登录、验证码或反爬限制。")
w("2. 逐校录取线均为第三方汇总数据，原文普遍注明「非官方发布、仅供参考、以学校/教育部门公布为准」。"
  "**不得用于真实志愿填报决策**，正式填报一律以西安市教育局及各校官方发布为准。")
w("3. 学费、住宿费、招生计划随年份与政策调整，务必核验当年公示。")
w("4. 2020–2021 数据由图片表格 OCR 转录，可能存在列错位，等级 D，已标注为「仅作背景参考」，"
  "**不应参与任何计算或模型训练的数值推理**。")
w("5. 所有数据来源 URL、抓取日期、可信等级均可追溯；如需对外发布，请先逐一复核版权与引用规范。")
w()

md = "\n".join(M) + "\n"
md_path = DOCS / "西安中考数据知识库.md"
md_path.write_text(md, encoding="utf-8")
print(f"Markdown 已生成：{md_path}  ({len(md)} 字符)")


# ---------------------------------------------------------------- Markdown -> HTML
def inline(s: str) -> str:
    s = html_mod.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_to_html(text: str) -> str:
    out: list[str] = []
    lines_iter = text.splitlines()
    i = 0
    in_ul = False
    while i < len(lines_iter):
        ln = lines_iter[i]
        if in_ul and not ln.startswith("- "):
            out.append("</ul>")
            in_ul = False
        if ln.startswith("|") and i + 1 < len(lines_iter) and re.match(r"^\|[\s\-|:]+\|$", lines_iter[i + 1]):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            body = []
            while i < len(lines_iter) and lines_iter[i].startswith("|"):
                body.append([c.strip() for c in lines_iter[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>")
            for r in body:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue
        if ln.startswith("### "):
            out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("> "):
            out.append(f"<blockquote>{inline(ln[2:])}</blockquote>")
        elif ln.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(ln[2:])}</li>")
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.strip() == "":
            pass
        else:
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 15mm 13mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "SimSun", sans-serif; font-size: 10pt;
       line-height: 1.65; color: #1c2530; margin: 0; }
h1 { font-size: 23pt; color: #14416f; border-bottom: 3px solid #2b6cb0;
     padding-bottom: 10px; margin: 0 0 18px; }
h2 { font-size: 15pt; color: #14416f; margin: 22px 0 10px;
     border-left: 5px solid #2b6cb0; padding-left: 10px; break-after: avoid; }
h3 { font-size: 11.5pt; color: #1d4e89; margin: 14px 0 6px; break-after: avoid; }
p { margin: 5px 0; }
blockquote { background: #eef4fb; border-left: 4px solid #7aa9d6; margin: 8px 0;
             padding: 7px 12px; color: #26445f; }
ul { margin: 5px 0 8px; padding-left: 22px; }
li { margin: 2px 0; }
hr { border: none; border-top: 1px solid #d6e0ea; margin: 20px 0; }
table { width: 100%; border-collapse: collapse; font-size: 7.8pt; margin: 8px 0 14px; }
thead { display: table-header-group; }
th { background: #e8f0f9; color: #14416f; font-weight: 600; text-align: left;
     border: 1px solid #c6d6e6; padding: 4px 5px; }
td { border: 1px solid #dde5ee; padding: 3px 5px; vertical-align: top; }
tr { break-inside: avoid; }
tbody tr:nth-child(even) { background: #f8fafc; }
code { background: #f0f3f7; padding: 1px 3px; border-radius: 3px;
       font-family: Consolas, monospace; font-size: 8.5pt; }
strong { color: #14416f; }
h2, h3 { page-break-after: avoid; }
"""

html_doc = ("<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<title>西安中考数据知识库</title><style>" + CSS + "</style></head><body>"
            + md_to_html(md) + "</body></html>")
html_path = BUILD / "knowledge.html"
html_path.write_text(html_doc, encoding="utf-8")

# ---------------------------------------------------------------- HTML -> PDF
candidates = [
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
]
browser = next((p for p in candidates if p.exists()), None)
pdf_path = DOCS / "西安中考数据知识库.pdf"
if browser is None:
    print("未找到 Chrome/Edge，跳过 PDF 生成（HTML 已保留在 docs/.build/）")
else:
    cmd = [str(browser), "--headless", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--print-to-pdf-no-header",
           "--virtual-time-budget=20000",
           f"--print-to-pdf={pdf_path}", html_path.as_uri()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if pdf_path.exists() and pdf_path.stat().st_size > 10000:
            print(f"PDF 已生成：{pdf_path}  ({pdf_path.stat().st_size // 1024} KB)")
        else:
            print("PDF 生成失败：", (r.stderr or r.stdout)[-400:])
    except Exception as e:
        print("PDF 生成异常：", type(e).__name__, str(e)[:200])
