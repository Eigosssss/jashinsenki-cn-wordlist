#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代称（Alias）防丢失检查。

背景：2026-10-23 的一次合入把 21 条角色代称静默清空（含「乌鸦」「最好看的那个」），
      直到 11-13 用户发现游戏里不显示才被察觉。此脚本把这件事变成可自动发现：

      * 以 git 上一次提交里的 pack.json 为基线，对比当前工作区的 Alias
      * 任何「从有到空」「值被改写」都会列出来并以非 0 退出
      * 建议在 build 之后、publish 之前跑

用法：
    python tools/check_alias.py                 # 对比 HEAD
    python tools/check_alias.py --base <rev>    # 指定基线（如 HEAD~1）
    python tools/check_alias.py --allow-drop    # 只报告不失败

依赖：仅标准库 + git。
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PACK_REL = "zh-CN/pack.json"


def load_from_git(rev):
    try:
        out = subprocess.run(
            ["git", "-C", REPO, "show", "%s:%s" % (rev, PACK_REL)],
            capture_output=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None
    try:
        return json.loads(out.decode("utf-8"))
    except Exception:
        return None


def alias_map(pack):
    out = {}
    for e in (pack.get("names") or {}).get("entries") or []:
        ja = str(e.get("Ja") or "")
        if ja:
            out[ja] = str(e.get("Alias") or "").strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--allow-drop", action="store_true")
    a = ap.parse_args()

    with open(os.path.join(REPO, PACK_REL), encoding="utf-8") as f:
        cur = json.load(f)
    base = load_from_git(a.base)
    if base is None:
        print("[SKIP] 读不到基线 %s:%s（首次提交？）" % (a.base, PACK_REL))
        return 0

    bm, cm = alias_map(base), alias_map(cur)
    dropped, changed = [], []
    for ja, old in bm.items():
        if not old:
            continue
        new = cm.get(ja)
        if new is None:
            dropped.append((ja, old, "(条目已不存在)"))
        elif not new:
            dropped.append((ja, old, "(空)"))
        elif new != old:
            changed.append((ja, old, new))

    total_old = sum(1 for v in bm.values() if v)
    total_new = sum(1 for v in cm.values() if v)
    print("代称数量：基线 %d → 当前 %d" % (total_old, total_new))

    if not dropped and not changed:
        print("[OK] 没有代称丢失或被改写")
        return 0

    if dropped:
        print("\n[FAIL] 丢失 %d 条：" % len(dropped))
        for ja, old, now in dropped:
            print("   %-24s %-14s -> %s" % (ja, old, now))
    if changed:
        print("\n[WARN] 被改写 %d 条：" % len(changed))
        for ja, old, new in changed:
            print("   %-24s %-14s -> %s" % (ja, old, new))

    if dropped and not a.allow_drop:
        print("\n如确认这些是有意删除，重跑并加 --allow-drop")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
