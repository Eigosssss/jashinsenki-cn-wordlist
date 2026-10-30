#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""词表覆盖率审计（独立版，随仓库分发）。

作用：把抓包里「会显示日文的文本」逐类与 pack.json 对照，找出**还没翻译**的条目。
     规则（类目清单、排除项）在 tools/audit-rules.json 里，随仓库同步，
     任何设备 pull 后都用同一套规则，不会因为换机器而漏查。

用法：
    python tools/audit_coverage.py --master <含 MasterData 的目录>
    python tools/audit_coverage.py --master <目录> --pack zh-CN/pack.json --json

依赖：仅 Python 3.8+ 标准库。
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RULES = os.path.join(HERE, "audit-rules.json")


def norm(s):
    """与插件 TextNormalizer 近似的归一化：去空白/零宽、统一换行。"""
    if not isinstance(s, str):
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff"):
        s = s.replace(ch, "")
    return re.sub(r"[\s\u3000]+", "", s)


def load_pack(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def covered_set(pack):
    out = set()
    for e in (pack.get("names") or {}).get("entries") or []:
        if e.get("Ja"):
            out.add(norm(e["Ja"]))
    for e in (pack.get("profiles") or {}).get("entries") or []:
        for k in ("titleJa", "textJa"):
            if e.get(k):
                out.add(norm(e[k]))
    for e in (pack.get("extras") or {}).get("entries") or []:
        if e.get("ja") and str(e.get("zh") or "").strip():
            out.add(norm(e["ja"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True, help="含 MasterData 的目录")
    ap.add_argument("--pack", default=os.path.join(HERE, "..", "zh-CN", "pack.json"))
    ap.add_argument("--rules", default=DEFAULT_RULES)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    with open(a.rules, encoding="utf-8") as f:
        rules = json.load(f)
    pack = load_pack(a.pack)
    have = covered_set(pack)

    data_dir = os.path.join(a.master, "MasterData", "data")
    if not os.path.isdir(data_dir):
        data_dir = os.path.join(a.master, "data")
    if not os.path.isdir(data_dir):
        sys.exit("[FAIL] 找不到 data 目录，检查 --master 是否指向含 MasterData 的那层")

    skip_fields = set(rules.get("skipFieldNames") or [])
    skip_prefix = tuple(rules.get("skipPrefix") or ())
    ph = re.compile(rules.get("placeholderPattern") or r"$^")
    cats = rules.get("categories") or []

    results = []
    for c in cats:
        path = os.path.join(data_dir, c["file"])
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                recs = json.load(f).get("records") or []
        except Exception:
            continue
        field = c["field"]
        vals, seen = [], set()
        for r in recs:
            if not isinstance(r, dict):
                continue
            v = r.get(field)
            if not isinstance(v, str) or field in skip_fields:
                continue
            v = v.strip()
            if not v or v.startswith(skip_prefix) or ph.search(v):
                continue
            if not re.search(r"[ぁ-んァ-ヶ]", v):
                continue
            if v in seen:
                continue
            seen.add(v)
            vals.append(v)
        miss = [v for v in vals if norm(v) not in have]
        results.append({
            "category": c["label"], "file": c["file"], "field": field,
            "excluded": bool(c.get("excluded")),
            "total": len(vals), "covered": len(vals) - len(miss), "missing": len(miss),
            "samples": miss[:8],
        })

    # 档案单独按 (groupId, level) 核
    prof_path = os.path.join(data_dir, "profile_description_data.json")
    if os.path.exists(prof_path):
        with open(prof_path, encoding="utf-8") as f:
            recs = json.load(f).get("records") or []
        prof = {(e.get("groupId"), e.get("level")) for e in (pack.get("profiles") or {}).get("entries") or []
                if str(e.get("titleZh") or "").strip() and str(e.get("textZh") or "").strip()}
        total = missn = 0
        samples = []
        for rec in recs:
            g = rec.get("id")
            for blk in rec.get("datas") or []:
                total += 1
                if (g, blk.get("level")) not in prof:
                    missn += 1
                    if len(samples) < 8:
                        samples.append("g%s lv%s %s" % (g, blk.get("level"), (blk.get("title") or "")[:30]))
        results.append({"category": "角色档案（标题+正文）", "file": "profile_description_data.json",
                        "field": "title/text", "excluded": False,
                        "total": total, "covered": total - missn, "missing": missn, "samples": samples})

    if a.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
        return 0

    print("%-24s %-30s %6s %6s %6s %7s" % ("类目", "表/字段", "总", "已覆盖", "缺", "覆盖率"))
    print("-" * 88)
    for r in sorted(results, key=lambda x: -x["missing"]):
        pct = r["covered"] / r["total"] * 100 if r["total"] else 100.0
        flag = ""
        if r["missing"] and not r["excluded"]:
            flag = "  <== 待补"
        elif r["missing"]:
            flag = "  (已排除)"
        print("%-24s %-30s %6d %6d %6d %6.1f%%%s"
              % (r["category"][:24], ("%s::%s" % (r["file"], r["field"]))[:30],
                 r["total"], r["covered"], r["missing"], pct, flag))

    todo = [r for r in results if r["missing"] and not r["excluded"]]
    print()
    if todo:
        print("=== 仍需补齐（%d 个类目） ===" % len(todo))
        for r in todo:
            print("\n[%s] 缺 %d" % (r["category"], r["missing"]))
            for s in r["samples"]:
                print("    ", repr(s[:80]))
    else:
        print("[OK] 所有需翻译类目均已覆盖（剩余缺口都在排除清单内）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
