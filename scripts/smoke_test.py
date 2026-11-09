# -*- coding: utf-8 -*-
"""v0.3 升级后端冒烟测试：账号隔离 / 方案 / 分享 / 对比 / 原有接口回归。

用法（先启动后端）：
    cd backend && .venv/Scripts/python.exe ../scripts/smoke_test.py
每次运行会创建带时间戳的临时账号，不会污染固定数据。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
STAMP = str(int(time.time()))
USER_A, USER_B = f"smoke_a_{STAMP}", f"smoke_b_{STAMP}"
PASSWORD = "test123456"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def call(method: str, path: str, data=None, token: str | None = None, timeout=150):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    safe_path = urllib.parse.quote(path, safe="/?&=%:,")
    req = urllib.request.Request(BASE + safe_path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def check(label: str, condition: bool, extra=""):
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}{(' -> ' + str(extra)) if extra else ''}")
    if not condition:
        raise AssertionError(label)


def main():
    print("=" * 62)
    print("v0.3 冒烟测试 | 账号", USER_A, "/", USER_B)
    print("=" * 62)

    # 0. 健康检查
    status, _ = call("GET", "/health")
    check("健康检查", status == 200, status)

    # 1. 注册 / 登录 / me
    status, reg_a = call("POST", "/auth/register", {
        "username": USER_A, "password": PASSWORD, "display_name": "考生甲",
    })
    check("注册账号 A", status == 200 and "token" in reg_a, status)
    token_a = reg_a["token"]

    status, dup = call("POST", "/auth/register", {"username": USER_A, "password": PASSWORD})
    check("重名注册被拒绝", status == 400, dup.get("detail"))

    status, bad = call("POST", "/auth/login", {"username": USER_A, "password": "wrong"})
    check("错误密码被拒绝", status == 400, bad.get("detail"))

    status, logged = call("POST", "/auth/login", {"username": USER_A, "password": PASSWORD})
    check("登录成功", status == 200 and logged["user"]["username"] == USER_A, status)

    status, me = call("GET", "/auth/me", token=token_a)
    check("令牌可解析当前用户", status == 200 and me["user"]["display_name"] == "考生甲", me)
    status, anon = call("GET", "/auth/me")
    check("无令牌时 me 返回空用户", status == 200 and anon["user"] is None, anon)

    status, reg_b = call("POST", "/auth/register", {"username": USER_B, "password": PASSWORD})
    check("注册账号 B", status == 200, status)
    token_b = reg_b["token"]

    # 2. 匿名报告仍可见，登录后按账号隔离
    status, anon_reports = call("GET", "/reports")
    check("未登录可见历史匿名报告", status == 200, f"{len(anon_reports)} 条")
    status, b_reports = call("GET", "/reports", token=token_b)
    check("新账号 B 看不到别人的报告", status == 200 and len(b_reports) == 0, len(b_reports))

    # 3. 推荐结果挂到当前账号
    profile = {
        "predicted_rank": 12000, "target_districts": [], "require_dormitory": False,
        "school_type_preference": "不限", "top_k": 5,
    }
    status, rec = call("POST", "/recommend", profile, token=token_a)
    check("登录态推荐正常", status == 200 and "profile_id" in rec,
          f"冲{len(rec.get('冲', []))}/稳{len(rec.get('稳', []))}/保{len(rec.get('保', []))}")

    # 4. AI 报告写入账号归属（真实调用一次 DeepSeek / 或自动降级）
    status, rep = call("POST", "/report", {**profile, "profile_id": rec["profile_id"]}, token=token_a)
    check("AI 报告生成", status == 200 and len(rep.get("content", "")) > 100,
          f"model={rep.get('model')} fallback={rep.get('fallback')} 字数={len(rep.get('content', ''))}")
    status, a_reports = call("GET", "/reports", token=token_a)
    check("账号 A 可见本人报告", status == 200 and any(r["id"] == rep["report_id"] for r in a_reports),
          len(a_reports))
    status, forbidden = call("GET", f"/reports/{rep['report_id']}", token=token_b)
    check("账号 B 无法读取 A 的报告", status == 403, forbidden.get("detail"))

    # 5. 方案必须登录
    status, _ = call("POST", "/plans", {"name": "匿名方案"})
    check("未登录保存方案被拒绝", status == 401, status)

    plan_payload_a = {
        "name": "稳妥版 · 位次12000",
        "profile": {"predicted_rank": 12000, "target_districts": [], "school_type_preference": "不限"},
        "volunteers": [
            {"order": 1, "school_id": 1, "name": "学校A", "strategy": "冲", "ref_rank": 9000},
            {"order": 2, "school_id": 2, "name": "学校B", "strategy": "稳", "ref_rank": 13000},
            {"order": 3, "school_id": 3, "name": "学校C", "strategy": "保", "ref_rank": 18000},
        ],
        "summary": {"counts": {"冲": 1, "稳": 1, "保": 1}, "issues": []},
    }
    plan_payload_b = {
        **plan_payload_a,
        "name": "冲刺版 · 位次12000",
        "volunteers": plan_payload_a["volunteers"][:2],
        "summary": {"counts": {"冲": 1, "稳": 1, "保": 0}, "issues": ["保档缺失"]},
    }
    status, plan_a = call("POST", "/plans", plan_payload_a, token=token_a)
    check("保存方案 1", status == 200 and plan_a["name"] == plan_payload_a["name"], status)
    status, plan_b = call("POST", "/plans", plan_payload_b, token=token_a)
    check("保存方案 2", status == 200, status)

    status, plans = call("GET", "/plans", token=token_a)
    check("方案列表返回 2 套", status == 200 and len(plans) == 2, len(plans))
    status, plans_b = call("GET", "/plans", token=token_b)
    check("账号 B 的方案列表为空", status == 200 and len(plans_b) == 0, len(plans_b))
    status, detail = call("GET", f"/plans/{plan_a['id']}", token=token_b)
    check("跨账号读取方案被拒绝", status == 403, detail.get("detail"))

    status, updated = call("PUT", f"/plans/{plan_a['id']}", {"name": "稳妥版(已重命名)"}, token=token_a)
    check("重命名方案", status == 200 and updated["name"] == "稳妥版(已重命名)", status)

    # 6. 分享链接（公开只读）
    status, share = call("POST", f"/plans/{plan_a['id']}/share", token=token_a)
    check("生成分享链接", status == 200 and "share_token" in share, share.get("share_path"))
    status, public = call("GET", f"/share/{share['share_token']}")
    check("免登录可读分享内容", status == 200 and len(public["volunteers"]) == 3,
          f"owner={public.get('owner')}")
    status, revoked = call("DELETE", f"/plans/{plan_a['id']}/share", token=token_a)
    check("撤销分享", status == 200, revoked)
    status, gone = call("GET", f"/share/{share['share_token']}")
    check("撤销后链接失效", status == 404, gone.get("detail"))

    # 7. 学校对比
    status, schools = call("GET", "/schools")
    ids = [s["id"] for s in schools[:4]]
    status, cmp_data = call("POST", "/schools/compare", {"school_ids": ids})
    check("对比 4 所学校", status == 200 and len(cmp_data["schools"]) == 4,
          f"首校={cmp_data['schools'][0]['name']} 中位数={cmp_data['schools'][0]['stats']['median_rank']}")
    status, too_many = call("POST", "/schools/compare", {"school_ids": list(range(1, 6))})
    check("超过 4 所被参数校验拦截", status == 422, status)

    # 8. 原有接口回归
    status, items = call("GET", "/talents/items")
    check("特长生项目接口", status == 200 and len(items["体育"]) > 0, f"体育{len(items['体育'])}项")
    status, talents = call("GET", "/talents/schools?category=体育&items=")
    check("特长生学校接口", status == 200 and len(talents["schools"]) > 0, len(talents["schools"]))
    check("特长生响应带逐年控制线 / 招生名额 / 模拟声明",
          len(talents["control_lines"]) == 6
          and any(s["sport_talent_plan"] is not None for s in talents["schools"])
          and "模拟" in talents["disclaimer"],
          f"控制线 {len(talents['control_lines'])} 年")
    check("招生计划项目无 OCR 错字「乓乓球」",
          all("乓乓球" not in (s["sport_items"] + s["art_items"])
              for s in talents["schools"]))
    _, any_match = call("GET", "/talents/schools?category=体育&items=田径,足球&match=any")
    _, all_match = call("GET", "/talents/schools?category=体育&items=田径,足球&match=all")
    check("「同时开设全部」是「任一命中」的子集",
          0 < all_match["total"] <= any_match["total"]
          and all({"田径", "足球"} <= set(s["matched_items"]) for s in all_match["schools"]),
          f"all={all_match['total']} any={any_match['total']}")
    status, bad_match = call("GET", "/talents/schools?category=体育&match=bad")
    check("非法匹配模式返回 400", status == 400, status)
    status, trend = call("GET", f"/schools/{ids[0]}/trend")
    check("位次趋势接口", status == 200 and len(trend) > 0, len(trend))
    status, check_v = call("POST", "/volunteer/check", {
        "predicted_rank": 12000, "school_ids": ids, "profile_id": rec["profile_id"],
    }, token=token_a)
    check("志愿梯度校验接口", status == 200 and len(check_v["items"]) == 4, len(check_v["items"]))
    status, bt = call("GET", "/backtest", timeout=120)
    check("回测接口", status == 200 and "top_sets" in bt, status)
    status, _ = call("GET", f"/reports/{rep['report_id']}", token=token_a)
    check("本人报告详情可读", status == 200, status)

    # 8.5 学校档案 v0.6（分区渐进式详情，全量学校回归）
    status, detail = call("GET", f"/schools/{ids[0]}/detail")
    check("学校档案详情结构", status == 200 and len(detail["sections"]) == 5
          and detail["coverage"]["total"] == 5, status)
    check("位次区块与完整度标记一致",
          detail["sections"]["rank"]["available"] == detail["school"]["has_rank_data"])
    check("住宿字段附数据来源说明", bool(detail["school"]["dormitory_note"]))
    check("住宿明确标注为模拟数据",
          "模拟" in detail["school"]["dormitory_text"]
          and "generate_dormitory_mock" in detail["school"]["dormitory_note"],
          detail["school"]["dormitory_text"])

    check("学校库收敛为 58 所", len(schools) == 58, f"{len(schools)} 所")
    check("全部学校均有历年位次", all(s["has_rank_data"] for s in schools),
          f"{sum(1 for s in schools if s['has_rank_data'])} 所有位次")

    bad: list[str] = []
    profile_hit = 0
    scale_sample = None
    for s in schools:
        code, d = call("GET", f"/schools/{s['id']}/detail")
        if code != 200 or d["coverage"]["total"] != 5:
            bad.append(s["name"])
            continue
        for key, sec in d["sections"].items():
            if not sec["available"] and not sec["reason"]:
                bad.append(f"{s['name']}/{key}(缺原因)")
        prof = d["sections"]["profile"]
        if prof["available"]:
            profile_hit += 1
            if not prof["fields"] or any(not f["value"] for f in prof["fields"]):
                bad.append(f"{s['name']}(档案空值)")
        al = d["sections"]["admission_lines"]
        if al["available"] and scale_sample is None:
            scale_sample = al["scales"]
    check("全量学校档案可打开且无空值", not bad,
          f"{len(schools)} 所，异常={bad[:3]}")
    check("校园档案只返回已采集字段", profile_hit > 0, f"{profile_hit} 所有档案")
    check("录取线按满分制分组", bool(scale_sample) and all(
        all(item["full_score"] == sc["full_score"] for item in sc["items"])
        for sc in scale_sample), f"{len(scale_sample or [])} 个分制")

    status, missing_school = call("GET", "/schools/999999/detail")
    check("不存在的学校返回 404", status == 404, missing_school.get("detail"))

    # 8.6 数据来源页「查看原件」：本地 PDF 必须返回真实文件，而不是 SPA 首页
    pdf_req = urllib.request.Request(
        BASE + "/source-files/" + urllib.parse.quote("2025城六区公办招生计划.pdf"))
    try:
        with urllib.request.urlopen(pdf_req, timeout=20) as resp:
            pdf_status = resp.status
            pdf_type = resp.headers.get("Content-Type", "")
            pdf_head = resp.read(5)
    except urllib.error.HTTPError as e:
        pdf_status, pdf_type, pdf_head = e.code, "", b""
    check("本地PDF原件可在线查看",
          pdf_status == 200 and "application/pdf" in pdf_type
          and pdf_head.startswith(b"%PDF"), pdf_status)
    try:
        with urllib.request.urlopen(
                urllib.request.Request(BASE + "/source-files/not-exist.pdf"), timeout=20) as resp:
            bad_status = resp.status
    except urllib.error.HTTPError as e:
        bad_status = e.code
    check("原件端点拒绝非白名单文件", bad_status == 404, bad_status)

    # 9. 登出
    status, _ = call("POST", "/auth/logout", token=token_b)
    status, after = call("GET", "/auth/me", token=token_b)
    check("登出后令牌失效", status == 200 and after["user"] is None, after)

    # 10. 清理本轮测试数据，保留学校/位次等基础数据
    for plan_id in (plan_a["id"], plan_b["id"]):
        call("DELETE", f"/plans/{plan_id}", token=token_a)

    print("=" * 62)
    print("全部通过 ✅  冒烟测试账号与方案已清理（用户表保留，可手动清理）")
    print("=" * 62)


if __name__ == "__main__":
    main()
