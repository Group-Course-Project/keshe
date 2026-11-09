# -*- coding: utf-8 -*-
"""
西安中考数据知识库 · 清洗与构建脚本（**历史采集脚本，已停用**）

!!! 2026-11-09 起系统只保留 58 校口径。本脚本会从 data/raw/web 原始快照
!!! 重新生成 124 校 / 428 条录取线的 CSV，运行即会覆盖已收敛的知识库。
!!! main() 内置保护：检测到 dataset_summary.json 的「数据口径」字段会直接拒绝运行。
!!! 确需重新采集时，请先阅读 README 的 58 校口径说明并同步更新文档与前端。

输入：
  data/raw/web/*.utf8.html          网页原始快照（带来源 URL 注释）
  data/raw/web/transcribed_*.csv   图片表格的人工核对转录
  data/raw/web/transcribed_score_rank_2025.txt
  data/raw/2025城六区*招生计划.pdf   教育局官方招生计划原件
  scripts/knowledge_seed.py         人工核对的静态种源（控制线、校园档案、来源清单）

输出（全部 UTF-8-BOM，Excel 可直接打开）：
  data/knowledge/*.csv
  data/knowledge/dataset_summary.json

设计原则：
  1. 不臆造数据：抓不到就留空，并在 备注 中说明。
  2. 每行带 来源ID 与 可信等级；同一 (学校,年份) 多来源时选优先级最高的为主记录，
     其余值写入「交叉校验值」列保留，便于复核。
  3. 分数不可跨年直接比较（2020-2024 为 700 分制，2025 为 820 分制），
     因此保留「总分满分」列，并提供「得分率」列（统招线/满分）作为可比口径。
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge_seed import (  # noqa: E402
    ALIASES,
    CONTROL_LINES,
    FETCH_DATE,
    LINES_2020_2021,
    LINES_2022_BATCH2,
    SCHOOL_PROFILES,
    SOURCES,
)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "web"
OUT = ROOT / "data" / "knowledge"
OUT.mkdir(parents=True, exist_ok=True)

# 同一学校+年份的来源优先级（数字越小越优先）
PRIORITY = {"S06": 1, "S04": 2, "S07": 3, "S08": 4, "S05": 5, "S09": 9}
FULL_SCORE = {2020: 700, 2021: 700, 2022: 700, 2023: 700, 2024: 700, 2025: 820}


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    path = OUT / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:<40} {len(rows):>4} 行")


def read_seed(filename: str) -> str:
    """读取人工转录文件；部分编辑器会写入 UTF-8 BOM，统一用 utf-8-sig 去除。"""
    return (RAW / filename).read_text(encoding="utf-8-sig")


def plain_text(filename: str) -> str:
    t = (RAW / filename).read_text(encoding="utf-8", errors="ignore")
    t = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t)
    p = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    return re.sub(r"[\s\xa0\u3000]+", " ", p)


def load_standard_names() -> set[str]:
    with (ROOT / "data" / "processed" / "schools.csv").open(encoding="utf-8-sig") as f:
        return {r["学校名称"] for r in csv.DictReader(f)}


STD_NAMES = load_standard_names()


def norm(name: str) -> tuple[str, str]:
    """返回 (标准校名, 匹配状态)"""
    name = re.sub(r"[（(](省示范|省标|普高|民办|公办|本部|南校区)[）)]", "", (name or "").strip())
    name = name.strip().strip("　 ")
    if name in STD_NAMES:
        return name, "匹配项目学校库"
    if name in ALIASES:
        target = ALIASES[name]
        return target, "匹配项目学校库" if target in STD_NAMES else "项目学校库外"
    for std in STD_NAMES:
        if std in name or name in std:
            return std, "模糊匹配(待核实)"
    return name, "项目学校库外"


def num(v) -> str:
    if v is None:
        return ""
    v = str(v).strip()
    return v if re.fullmatch(r"\d{3}(?:\.\d+)?", v) else ""


def score_rate(line, year) -> str:
    v = num(line)
    return f"{float(v) / FULL_SCORE[year] * 100:.2f}%" if v else ""


# ---------------------------------------------------------------- 1. 逐校录取线
records: dict[tuple[str, int], list[dict]] = {}


# 原表里有「本部」「宏志对等班」「民营机制」等班型/机制条目，不是学校，必须剔除
NON_SCHOOL = re.compile(r"^(本部|.*宏志对等班|.*民营机制|.*德语班|.*日语班|合计|小计)$")


def add(name: str, year: int, line, dt="", source="", level="", attr="", nature="",
        batch="", note="") -> None:
    name = (name or "").strip()
    if NON_SCHOOL.match(name) or len(name) < 3:
        return
    std, matched = norm(name)
    v = num(line)
    if not v and not dt:
        return
    key = (std, year)
    records.setdefault(key, []).append({
        "std": std, "raw": name, "matched": matched, "year": year,
        "line": v, "dt": num(dt), "source": source, "level": level,
        "attr": attr, "nature": nature, "batch": batch, "note": note,
    })


def parse_2025_xinshinet() -> int:
    p = plain_text("xinshinet_2025_lines.utf8.html")
    rows = re.findall(r"([\u4e00-\u9fa5（）A-Za-z0-9·]{3,25})[：:]\s*(\d{3}(?:\.\d)?)\s*分", p)
    for name, line in rows:
        if "第一批次" in name or "第二批次" in name:
            continue
        add(name, 2025, line, source="S06", level="C")
    # 重新按正文顺序标注批次
    text = p
    i1 = text.find("第一批次省示范高中")
    i2 = text.find("第二批次省标准")
    for name, line in rows:
        pos = text.find(name + "：" + line)
        if pos < 0:
            pos = text.find(name + ":" + line)
        b = "第一批次" if (i1 <= pos < i2) else "第二批次"
        for rec in records.get((norm(name)[0], 2025), []):
            if rec["source"] == "S06" and rec["line"] == line:
                rec["batch"] = b
    return len(rows)


def parse_2024_52zk() -> int:
    p = plain_text("52zk_2024_lines.utf8.html")
    seg = p[p.find("学校名称 统招线"):p.find("2024年西安市城六区")]
    rows = re.findall(
        r"([\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z0-9（）()]{2,24}?)\s*(\d{3}(?:\.\d)?)\s+(\d{3}(?:\.\d)?)", seg)
    for name, line, dt in rows:
        add(name, 2024, line, dt, source="S04", level="C", batch="第一批次")
    # 「长安区第一中学630.0 网传640」第三个值非数字，单独补
    add("长安区第一中学", 2024, "630.0", source="S04", level="C", batch="第一批次",
        note="定转统线原文为「网传640」，非确切值，未收录")
    return len(rows) + 1


def parse_2022_91zk() -> int:
    p = plain_text("zk91_2022_lines.utf8.html")
    start = p.find("西工大附中670")
    seg = p[start:p.find("西安中考", start)] if start >= 0 else ""
    # 「高新一中665（本部669) 663」里的括注是校区线，去掉以免被拆成一条名为「本部」的学校
    seg = re.sub(r"[（(]本部\s*\d+[）)]", "", seg)
    rows = re.findall(
        r"([\u4e00-\u9fa5][\u4e00-\u9fa5A-Za-z0-9（）()]{1,24}?)\s*(\d{3}(?:\.\d)?)(?:\s+(\d{3}(?:\.\d)?))?", seg)
    n = 0
    for name, line, dt in rows:
        if not name or len(name) < 2:
            continue
        add(name, 2022, line, dt, source="S07", level="C", batch="第一批次")
        n += 1
    return n


def parse_transcribed_3y() -> int:
    lines = [x for x in read_seed("transcribed_2023_2025.csv").splitlines()
             if x and not x.startswith("#")]
    reader = csv.DictReader(lines)
    n = 0
    for r in reader:
        attr, nature, batch = r["学校属性"], r["办学性质"], r["招生批次"]
        for year, col in [(2023, "2023统招线"), (2024, "2024统招线"), (2025, "2025统招线")]:
            v = r[col].strip()
            note = ""
            if v and not re.fullmatch(r"\d{3}(?:\.\d)?", v):
                note = f"原表值为「{v}」，非确定分数，未收录"
                v = ""
            if v:
                add(r["学校名称"], year, v, source="S05", level="C",
                    attr=attr, nature=nature, batch=batch, note=note)
                n += 1
    return n


def parse_seed_lines() -> None:
    for name, l21, l20, note in LINES_2020_2021:
        add(name, 2021, l21, source="S09", level="D", note=note or "OCR 转录，列对齐存在误差，仅作背景参考")
        add(name, 2020, l20, source="S09", level="D", note=note or "OCR 转录，列对齐存在误差，仅作背景参考")
    for name, line in LINES_2022_BATCH2:
        add(name, 2022, line, source="S08", level="C", batch="第二批次",
            note="转录自 52中考网 2022 第二批次汇总")


def build_admission_lines() -> list[list]:
    parse_2025_xinshinet()
    parse_2024_52zk()
    parse_2022_91zk()
    parse_transcribed_3y()
    parse_seed_lines()

    rows = []
    for (std, year), recs in sorted(records.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        recs.sort(key=lambda r: PRIORITY.get(r["source"], 99))
        main = recs[0]
        others = [f"{r['source']}:{r['line']}" for r in recs[1:] if r["line"]]
        # 属性/性质/批次从任意来源补齐
        attr = next((r["attr"] for r in recs if r["attr"]), "")
        nature = next((r["nature"] for r in recs if r["nature"]), "")
        batch = next((r["batch"] for r in recs if r["batch"]), "")
        notes = "; ".join(dict.fromkeys(r["note"] for r in recs if r["note"]))
        rows.append([
            std, main["raw"], main["matched"], year, FULL_SCORE[year],
            main["line"], main["dt"], score_rate(main["line"], year),
            attr, nature, batch, main["source"], main["level"],
            "; ".join(dict.fromkeys(others)), notes,
        ])
    write_csv("admission_lines_2020_2025.csv", [
        "标准校名", "原始校名", "匹配状态", "年份", "总分满分", "统招线", "定转统线",
        "得分率", "学校属性", "办学性质", "招生批次", "来源ID", "可信等级", "交叉校验值", "备注",
    ], rows)
    return rows


# ---------------------------------------------------------------- 2. 控制线 / 一分一段
def build_control_lines() -> list[list]:
    rows = [list(r) for r in CONTROL_LINES]
    write_csv("control_lines_2020_2025.csv", [
        "年份", "招生单元", "总分满分", "普高录取控制线", "体艺特长生控制线",
        "综合高中班控制线", "来源ID", "可信等级", "备注",
    ], rows)
    return rows


def build_score_rank_map() -> list[list]:
    rows = []
    for line in read_seed("transcribed_score_rank_2025.txt").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) != 3:
            continue
        score, rank, ratio = parts
        rows.append(["城六区", 2025, 820, score, "" if rank == "屏蔽" else rank,
                     ratio, "S10", "C",
                     "屏蔽：特高分段延迟公布具体分数" if rank == "屏蔽" else ""])
    write_csv("score_rank_map_2025.csv", [
        "招生单元", "年份", "总分满分", "中考成绩", "城六区累计位次", "位比%",
        "来源ID", "可信等级", "备注",
    ], rows)
    return rows


# ---------------------------------------------------------------- 3. 官方招生计划 PDF
def parse_plan_pdf(path: Path, kind: str) -> list[list]:
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                continue
            for row in tables[0]:
                first = (row[0] or "").replace("\n", "").strip()
                if not re.fullmatch(r"\d+", first):
                    continue
                name = re.sub(r"[（(].*?[）)]", "", (row[1] or "").replace("\n", "")).strip()
                std, matched = norm(name)

                def cell(i):
                    return (row[i] or "").replace("\n", "").strip() if len(row) > i else ""

                # 两种版式：公办 18 列 / 民办 14 列
                if kind == "公办":
                    sports_items, arts_items = cell(15), cell(16)
                    talent_sport, talent_art = cell(9), cell(10)
                    single = " / ".join(x for x in [cell(12), cell(13), cell(14)] if x)
                    feature = cell(5)
                else:
                    sports_items, arts_items = cell(11), cell(12)
                    talent_sport, talent_art = cell(9), ""
                    single = cell(10)
                    feature = cell(5)
                rows.append([
                    std, name, matched, kind, 2025,
                    cell(2), cell(3), cell(6), talent_sport, talent_art,
                    feature, sports_items, arts_items, single, "S11", "A",
                    "来源：西安市教育局 2025 城六区%s招生计划 PDF 原件" % kind,
                ])
    return rows


def build_enrollment_plan() -> list[list]:
    rows = []
    for fn, kind in [("2025城六区公办招生计划.pdf", "公办"), ("2025城六区民办招生计划.pdf", "民办")]:
        rows += parse_plan_pdf(ROOT / "data" / "raw" / fn, kind)
    write_csv("enrollment_plan_2025.csv", [
        "标准校名", "PDF原始校名", "匹配状态", "办学性质", "年份",
        "招生计划总数", "统招生计划", "定向生计划", "体育特长生计划", "艺术特长生计划",
        "特色班类别", "体育类特长项目", "艺术类特长项目", "单列计划", "来源ID", "可信等级", "备注",
    ], rows)
    return rows


# ---------------------------------------------------------------- 4. 校园档案 / 扩展名录 / 来源
def build_profiles() -> list[list]:
    rows = []
    for p in SCHOOL_PROFILES:
        name, addr, code, site, tel, fee, dorm_fee, board, plan, talent, feature, url, level = p
        std, matched = norm(name)
        rows.append([std, name, matched, addr, code, site, tel, fee, dorm_fee,
                     board, plan, talent, feature, url, level, FETCH_DATE])
    write_csv("school_profiles.csv", [
        "标准校名", "原始校名", "匹配状态", "学校地址", "招生代码", "官网", "咨询电话",
        "学费", "住宿费", "食宿条件", "2025招生计划", "特长生信息", "办学特色/简介",
        "来源URL", "可信等级", "抓取日期",
    ], rows)
    return rows


def build_directory() -> list[list]:
    lines = [x for x in read_seed("transcribed_2023_2025.csv").splitlines()
             if x and not x.startswith("#")]
    rows = []
    for r in csv.DictReader(lines):
        std, matched = norm(r["学校名称"])
        rows.append([r["序号"], std, r["学校名称"], matched, r["学校属性"],
                     r["办学性质"], r["招生批次"], "S05", "C"])
    write_csv("school_directory_extended.csv", [
        "序号", "标准校名", "原始校名", "匹配状态", "学校属性", "办学性质", "招生批次",
        "来源ID", "可信等级",
    ], rows)
    return rows


def build_sources() -> list[list]:
    rows = [[a, b, c, d, e, f, FETCH_DATE] for a, b, c, d, e, f in SOURCES]
    write_csv("data_sources.csv", [
        "来源ID", "来源名称", "URL", "类型", "可信等级", "说明", "抓取日期",
    ], rows)
    return rows


def main() -> None:
    summary_path = OUT / "dataset_summary.json"
    if summary_path.exists() and "数据口径" in summary_path.read_text(encoding="utf-8"):
        raise RuntimeError(
            "本脚本会从原始快照重建 124 校口径 CSV，已停用（当前系统只保留 58 校）。"
            "如确需重新采集，请先移除本保护并同步更新 build_knowledge_doc.py / README / 前端文案。"
        )
    print("构建西安中考数据知识库 ...")
    lines = build_admission_lines()
    controls = build_control_lines()
    ranks = build_score_rank_map()
    plans = build_enrollment_plan()
    profiles = build_profiles()
    directory = build_directory()
    sources = build_sources()

    by_year: dict[int, int] = {}
    for r in lines:
        by_year[r[3]] = by_year.get(r[3], 0) + 1
    matched = sum(1 for r in lines if r[2] == "匹配项目学校库")
    official = sum(1 for r in lines if r[12] == "A")
    summary = {
        "抓取日期": FETCH_DATE,
        "逐校录取线记录": len(lines),
        "各年份记录数": dict(sorted(by_year.items())),
        "覆盖学校数": len({r[0] for r in lines}),
        "其中匹配项目现有学校库": len({r[0] for r in lines if r[2] == "匹配项目学校库"}),
        "匹配记录数": matched,
        "官方A级记录数": official,
        "控制线年份数": len(controls),
        "一分一段分数档位数": len(ranks),
        "官方招生计划学校数": len(plans),
        "其中含特长生项目": sum(1 for r in plans if r[11] or r[12]),
        "校园档案数": len(profiles),
        "扩展学校名录": len(directory),
        "数据源数": len(sources),
        "总分口径": {"2020-2024": 700, "2025": 820, "2026起": 640},
        "重要提示": "除控制线、招生计划、学校官网简章外，逐校录取线均为第三方汇总（非官方发布）；"
                    "2025年起总分由700改为820，跨年分数不可直接比较，请用得分率或位次。",
    }
    (OUT / "dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n=== 数据集摘要 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
