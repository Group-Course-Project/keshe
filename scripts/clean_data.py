# -*- coding: utf-8 -*-
"""
清洗《表格_20261101.csv》：
1. 校名标准化 + 补充 城区 / 公办民办（来自西安市教育局 2025 招生计划）
2. 是否住宿：按用户要求随机 mock（随机种子固定，可复现）
3. 位次值规范化：左右 / 补录 / —— / 边界 / 区间 / 缺失
4. 仅保留城六区（碑林/新城/莲湖/雁塔/未央/灞桥）
产出：data/processed/schools.csv、data/processed/enrollment_records.csv
"""
import csv
import random
from pathlib import Path

SRC = Path(r"C:/Users/liang'yi'yang/Downloads/表格_20261101.csv")
OUT_DIR = Path(r"data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHENGLIU = {"碑林区", "新城区", "莲湖区", "雁塔区", "未央区", "灞桥区"}

# csv 原始校名 -> (标准校名, 城区, 办学性质, 备注)
MAPPING = {
    "西工大附中": ("西北工业大学附属中学", "碑林区", "公办", ""),
    "铁一中": ("西安市铁一中学", "碑林区", "公办", ""),
    "高新一中（本部）": ("西安高新第一中学", "雁塔区", "民办", ""),
    "交大附中": ("西安交通大学附属中学", "碑林区", "公办", ""),
    "师大附中": ("陕西师范大学附属中学", "雁塔区", "公办", ""),
    "滨河中学": ("西安铁一中滨河高级中学", "灞桥区", "民办", ""),
    "铁一中国际部": ("西安铁一中国际合作学校", "碑林区", "民办", ""),
    "高新一中南校区": ("西安高新第一中学南校区", "雁塔区", "民办", "按高新一中（民办）处理，南校区为其校区，待核实"),
    "西安中学": ("陕西省西安中学", "未央区", "公办", ""),
    "西安市三中": ("西安市第三中学", "碑林区", "公办", ""),
    "铁一中陆港中学": ("西安国际港务区铁一中陆港高级中学", "灞桥区", "公办", ""),
    "崇是中学": ("西安崇是中学", "雁塔区", "民办", ""),
    "交大创新港中学": ("西安市创新港中学", "西咸新区", "公办", "西咸新区，非城六区，已排除"),
    "西安市一中": ("西安市第一中学", "莲湖区", "公办", ""),
    "西安市 83 中": ("西安市第八十三中学", "新城区", "公办", ""),
    "铁一金湾": ("西咸新区铁一中金湾中学", "西咸新区", "公办", "西咸新区，非城六区，已排除"),
    "曲江一中": ("西安市曲江第一中学", "雁塔区", "公办", ""),
    "长安一中": ("西安市长安区第一中学", "长安区", "公办", "长安区，非城六区，已排除"),
    "西安市 85 中": ("西安市第八十五中学", "雁塔区", "公办", ""),
    "交大附中航天分校": ("西安交通大学附属中学航天高级中学", "雁塔区", "民办", ""),
    "高新一中陆港中学": ("西安国际港务区高新一中陆港中学", "灞桥区", "公办", ""),
    "西安市 26 中": ("西安市第二十六中学", "碑林区", "公办", ""),
    "西安市 89 中": ("西安市第八十九中学", "新城区", "公办", ""),
    "经开一中": ("西安市经开第一中学", "未央区", "公办", ""),
    "高新一中沣东中学": ("西安高新一中沣东中学", "西咸新区", "民办", "西咸新区，非城六区，已排除"),
    "西北大学附中": ("西北大学附属中学", "碑林区", "公办", ""),
    "西安湖滨": ("西安湖滨中学", "长安区", "民办", "疑长安区（原铁一中湖滨），非城六区，已排除；如有误请告知"),
    "交大空港实验中学": ("西咸新区空港实验高级中学", "西咸新区", "公办", "西咸新区，非城六区，已排除"),
    "高新二中": ("西安市高新第二高级中学", "雁塔区", "公办", ""),
    "高新一中实验中学": ("西安高新一中实验中学", "雁塔区", "公办", ""),
    "89 中分校": ("西安市第八十九中学分校", "新城区", "公办", ""),
    "航天城二中": ("西安市航天城第二中学", "雁塔区", "公办", ""),
    "航天城一中": ("西安市航天城第一中学", "雁塔区", "公办", ""),
    "秦汉中学": ("陕西省西咸新区秦汉中学", "西咸新区", "公办", "西咸新区，非城六区，已排除"),
    "西安高级中学": ("西安高级中学", "未央区", "公办", ""),
    "西光中学": ("西安市西光中学", "新城区", "公办", ""),
    "西电附中": ("西安电子科技大学附属中学", "雁塔区", "公办", ""),
    "西安市 8 中": ("西安市第八中学", "碑林区", "公办", ""),
    "西安市 6 中": ("西安市第六中学", "碑林区", "公办", ""),
    "唐南中学": ("西安高新唐南中学", "雁塔区", "民办", ""),
    "曲江二中": ("西安市曲江第二中学", "雁塔区", "公办", ""),
    "高新三中": ("西安高新第三中学", "雁塔区", "公办", ""),
    "75 中": ("西安市第七十五中学", "未央区", "公办", ""),
    "西航一中": ("西安市西航一中", "未央区", "公办", ""),
    "建大附中": ("西安建筑科技大学附属中学", "碑林区", "公办", ""),
    "东城一中": ("西安市东城第一中学", "灞桥区", "公办", ""),
    "庆安中学": ("西安市庆安高级中学", "莲湖区", "公办", ""),
    "72 中": ("西安市第七十二中学", "新城区", "公办", ""),
    "6 中分校": ("西安市第六中学分校", "碑林区", "公办", ""),
    "西大浐灞": ("西安市西大附中浐灞中学", "未央区", "公办", ""),
    "远东一中": ("西安市远东第一中学", "莲湖区", "公办", ""),
    "航天中学": ("西安市航天中学", "雁塔区", "公办", ""),
    "雁塔二中": ("西安市雁塔区第二中学", "雁塔区", "公办", ""),
    "82 中": ("西安市第八十二中学", "碑林区", "公办", ""),
    "远东二中": ("西安市远东第二中学", "莲湖区", "公办", ""),
    "五环中学": ("西安市五环中学", "灞桥区", "公办", ""),
    "西安市二中": ("西安市第二中学", "碑林区", "公办", ""),
    "66 中": ("西安市第六十六中学", "未央区", "公办", ""),
    "育才中学": ("西安市育才中学", "雁塔区", "公办", ""),
    "经开三中": ("西安市经开第三中学", "未央区", "公办", ""),
    "黄河中学": ("西安市黄河中学", "新城区", "公办", ""),
    "长安一民": ("西安市长安区第一民办中学", "长安区", "民办", "长安区，非城六区，已排除"),
    "阳光中学": ("西安市阳光中学", "雁塔区", "公办", ""),
    "含光中学": ("西安市含光中学", "碑林区", "公办", ""),
    "浐灞二中": ("西安市浐灞第二中学", "未央区", "公办", ""),
    "中铁学校": ("西安市中铁中学", "碑林区", "公办", ""),
}


def clean_rank(raw: str):
    """返回 (rank_int_or_None, status, raw)"""
    raw = (raw or "").strip()
    original = raw
    if raw == "":
        return None, "缺失", original
    if raw in ("/", "——"):
        return None, "无数据", original
    if "补录" in raw:
        return None, "补录", original
    if "万" in raw:
        # 形如 1.7-1.9 万
        nums = raw.replace("万", "").replace(" ", "").split("-")
        try:
            lo, hi = float(nums[0]), float(nums[1])
            return int((lo + hi) / 2 * 10000), "区间", original
        except Exception:
            return None, "异常", original
    s = raw.replace("左右", "").replace(" ", "").strip()
    boundary = None
    if s.startswith(">"):
        boundary = ">"
        s = s[1:]
    elif s.startswith("<"):
        boundary = "<"
        s = s[1:]
    if s.isdigit():
        val = int(s)
        if boundary:
            return val, f"边界{boundary}", original
        if "左右" in raw:
            return val, "约", original
        return val, "正常", original
    return None, "异常", original


def main():
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    data = rows[1:]

    years = [h.strip().split(" ")[0] for h in header[1:]]  # 2020..2025
    random.seed(42)

    schools = []  # (标准名, 城区, 性质, 住宿, 备注)
    records = []
    excluded = []
    unmatched = []

    for r in data:
        raw_name = r[0].strip()
        key = raw_name.lstrip("*").strip()
        if key not in MAPPING:
            unmatched.append(raw_name)
            continue
        std, district, nature, note = MAPPING[key]
        if district not in CHENGLIU:
            excluded.append((raw_name, district, nature, note))
            continue
        dormitory = random.randint(0, 1)
        schools.append((std, district, nature, dormitory, note))
        for yi, cell in enumerate(r[1:]):
            year = years[yi]
            rank, status, original = clean_rank(cell)
            records.append((std, year, "" if rank is None else rank, status, original))

    # 写学校表
    with open(OUT_DIR / "schools.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["学校名称", "城区", "办学性质", "是否住宿", "备注"])
        for row in schools:
            w.writerow(row)

    # 写位次表
    with open(OUT_DIR / "enrollment_records.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["学校名称", "年份", "最低位次", "位次状态", "原始值"])
        w.writerows(records)

    print("保留学校数:", len(schools))
    print("位次记录数:", len(records))
    print("排除学校数:", len(excluded))
    for raw, d, n, note in excluded:
        print("  排除:", raw, "->", d, n, note)
    if unmatched:
        print("未匹配:", unmatched)
    from collections import Counter
    cnt = Counter((y, s) for _, y, _, s, _ in records)
    print("\n各位次状态统计(年份,状态):")
    for k in sorted(cnt):
        print(" ", k, cnt[k])


if __name__ == "__main__":
    main()
