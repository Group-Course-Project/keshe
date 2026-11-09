"""统计数据库中西安高中的覆盖情况，并给出校名归一后的实体数估算。

用法（项目根目录）：
    backend/.venv/Scripts/python.exe scripts/analyze_school_coverage.py

说明：主推荐库 school 使用一套校名，知识库各表使用「标准校名」，
其中存在同校不同写法（如「长安一中」/「西安市长安区第一中学」）。
本脚本用启发式规则做轻量归一，仅用于估算实体数，不修改任何数据。

注意（2026-11-09）：系统已收敛为 58 校口径，school 表与知识库均为 58 校。
本脚本的「库外学校 / 130 个校名」等估算结论是扩展前（119 校时期）的历史口径，
仅作审计参考，不得用于恢复已删除的 61 所仅资料学校。
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from backend.app.database import engine  # noqa: E402

CN = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
      "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
CN_PAT = r"[零一二三四五六七八九]十[零一二三四五六七八九]?|十[零一二三四五六七八九]|[零一二三四五六七八九]"


def cn2num(s: str) -> str:
    def repl(m):
        t = m.group()
        if len(t) == 1:
            return str(CN[t])
        if t.startswith("十"):
            return str(10 + CN[t[1]])
        if t.endswith("十"):
            return str(CN[t[0]] * 10)
        return str(CN[t[0]] * 10 + CN[t[2]])
    return re.sub(CN_PAT, repl, s)


PREFIXES = [
    "陕西省西咸新区", "西安市浐灞国际港", "西安市国际港务区", "西咸新区",
    "西安市高新区", "西安高新区", "西安市长安区", "陕西省",
    "西安市", "长安区", "西安",
]
# 最长匹配、只剥一次，避免「西安市长安区第一中学」被层层剥成「第一中学」
PREFIX_RE = re.compile("^(" + "|".join(sorted(PREFIXES, key=len, reverse=True)) + ")")


def norm(name: str) -> str:
    s = cn2num(name)
    s = PREFIX_RE.sub("", s)
    s = s.replace("附属中学", "附中").replace("高级中学", "中学")
    s = s.replace("陕西师范大学", "师大").replace("师大附中", "师大附属")
    s = re.sub(r"第(\d+)", r"\1", s)
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", s)


def main():
    with engine.connect() as c:
        main_schools = {r[0] for r in c.execute(text("select name from school"))}
        tables = {
            "school（主推荐库）": main_schools,
            "enrollment_plan": {r[0] for r in c.execute(text("select school_name from enrollment_plan"))},
            "admission_score": {r[0] for r in c.execute(text("select school_name from admission_score"))},
            "school_profile": {r[0] for r in c.execute(text("select school_name from school_profile"))},
        }
        rec = c.execute(text("select count(distinct school_id) from enrollment_record")).scalar()
        talent = c.execute(text("select count(distinct school_id) from school_talent")).scalar()

    print("=== 各表去重校名数 ===")
    for k, v in tables.items():
        print(f"  {k:<22} {len(v):>4} 所")
    print(f"  school 有位次记录          {rec:>4} 所")
    print(f"  school 有特长生项目        {talent:>4} 所")

    all_names = set().union(*tables.values())
    extra = set().union(*[v for k, v in tables.items() if k != "school（主推荐库）"])
    print("\n=== 覆盖关系 ===")
    print(f"  原始校名去重后并集        {len(all_names):>4} 个")
    print(f"  主库与扩展数据交集        {len(main_schools & extra):>4} 所")
    print(f"  仅主库、无扩展数据        {len(main_schools - extra):>4} 所 -> {sorted(main_schools - extra)}")
    print(f"  仅扩展数据、不在主库      {len(extra - main_schools):>4} 所")

    groups = defaultdict(list)
    for n in sorted(all_names):
        groups[norm(n)].append(n)
    dups = {k: v for k, v in groups.items() if len(v) > 1}
    print("\n=== 校名归一（估算真实实体）===")
    print(f"  归一后实体数（估算）      {len(groups):>4} 所")
    print(f"  识别别名组                {len(dups):>4} 组，合并掉 {sum(len(v) - 1 for v in dups.values())} 个重复写法")
    print("  注意：启发式归一存在已知误判（如「西安市第一中学」与「西安市长安区第一中学」"),
    print("        被误并），且未覆盖「长安一中」等简称，故此数仅供估算，不可作为精确口径。")
    for k, v in sorted(dups.items(), key=lambda x: -len(x[1]))[:15]:
        print("    " + " / ".join(v))


if __name__ == "__main__":
    main()
