# -*- coding: utf-8 -*-
import json
import os

from dotenv import load_dotenv

from ..config import BACKEND_DIR

load_dotenv(BACKEND_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def fallback_report(predicted_rank: int, grouped: dict, preferences: dict | None = None) -> str:
    school_pref = (preferences or {}).get("school_type_preference") or "不限"
    require_dormitory = bool((preferences or {}).get("require_dormitory"))
    lines = [
        "# 中考志愿填报分析报告（规则版）",
        "",
        f"考生预估位次：**{predicted_rank}**。本报告由规则模板生成，没接大模型，就当个有底气的参考。",
        "",
        "## 先说结论",
        "",
        "志愿这活儿不是赌一次，是给自己留退路。冲稳保排好，滑档这件事基本跟你没关系。",
        "",
    ]
    for tier in ("冲", "稳", "保"):
        items = grouped.get(tier, [])
        lines.append(f"## {tier}档（{len(items)} 所）")
        lines.append("")
        if not items:
            lines.append("这档暂时没学校，别硬凑。")
            lines.append("")
            continue
        for c in items:
            ref = c.get("ref_rank")
            lines.append(
                f"- **{c.get('name')}**（{c.get('district')} · {c.get('school_type')}）："
                f"参考位次 {ref}（截至 {c.get('ref_year')} 年），匹配分 {c.get('match_score')}"
            )
        lines.append("")
    lines += [
        "## 怎么填",
        "",
        "1. 冲档放 2–3 所就行，别把志愿表全押在“搏一搏”。",
        "2. 稳档是你的主战场，占到四成左右最舒服。",
        "3. 保底至少留 2 所，而且必须是你自己愿意读的，别为了不滑档塞个不去的。",
        "",
        "## 现实的账",
        "",
    ]
    if school_pref == "民办":
        lines.append("- 你选了民办方向：民办校别只看录取线，先算三年学费和生活费，这不是小钱。")
    if require_dormitory:
        lines.append("- 你要求住宿：住宿和走读差的不只是钱，还有每天的通勤，提前算清楚。")
    if school_pref == "不限" and not require_dormitory:
        lines.append("- 公办/民办、住宿/走读的成本差异，建议和家里摊开算一笔。")
    lines += [
        "",
        "## 风险提示",
        "",
        "以上结果基于历史投档位次估算，位次会跳、政策会变，仅供参考。正式填报请核对本省/市教育考试院当年官方文件，在官方平台自主填报。",
    ]
    return "\n".join(lines)


def generate_report(
    predicted_rank: int, grouped: dict, preferences: dict | None = None
) -> tuple[str, str, bool]:
    """返回 (报告内容, 模型名, 是否使用了降级模板)"""
    api_key = _env("DEEPSEEK_API_KEY")
    base_url = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = _env("DEEPSEEK_MODEL", "deepseek-chat")
    if not api_key:
        return fallback_report(predicted_rank, grouped, preferences), "mock", True

    compact = {"冲": [], "稳": [], "保": []}
    for tier in ("冲", "稳", "保"):
        for c in grouped.get(tier, []):
            compact[tier].append({
                "name": c.get("name"),
                "district": c.get("district"),
                "type": c.get("school_type"),
                "ref_rank": c.get("ref_rank"),
                "ref_year": c.get("ref_year"),
                "score": c.get("match_score"),
            })

    system = (
        "你是一名经验丰富的西安中考志愿咨询师，风格直白、风趣、不灌鸡汤，说话像靠谱的长辈。"
        "必须短句、节奏快：先给结论，再讲现实代价，最后给可执行方案，结尾用一句金句收束。"
        "不要夸大任何学校的录取确定性，不要承诺录取结果，不编造分数线和招生计划，必须提醒以官方数据为准。"
    )
    user_lines = [
        f"考生预估位次：{predicted_rank}",
        f"冲稳保候选（JSON）：\n{json.dumps(compact, ensure_ascii=False)}",
        "",
    ]
    pref = preferences or {}
    hints = []
    if pref.get("school_type_preference") == "民办":
        hints.append("家庭可接受民办：提示先算三年学费，别只看录取线。")
    elif pref.get("school_type_preference") == "公办":
        hints.append("家庭倾向公办：把公办作为主建议方向。")
    if pref.get("require_dormitory"):
        hints.append("考生要求住宿：提示走读与住宿的成本、通勤差异。")
    if pref.get("target_districts"):
        hints.append("目标城区：" + "、".join(pref["target_districts"]) + "。")
    if hints:
        user_lines.append("考生家庭背景线索：")
        user_lines.extend("- " + h for h in hints)
        user_lines.append("")
    user_lines += [
        "请用 Markdown 输出，包含：总体判断、冲/稳/保逐档分析、填报顺序建议、风险提示。",
        "控制在 600 字以内，语言面向家长，幽默但不轻浮，不输出“推荐购买”类广告。",
    ]
    user = "\n".join(user_lines)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4,
            max_tokens=1200,
        )
        return resp.choices[0].message.content or "", model, False
    except Exception:
        return fallback_report(predicted_rank, grouped, preferences), "mock", True
