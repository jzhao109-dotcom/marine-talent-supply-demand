#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
from collections import Counter
from pathlib import Path


INPUT_DIR = Path("供需能力开放编码_中观边界强化口径_全量")
SUPPLY_FILE = INPUT_DIR / "supply_competency_items_coded.csv"
DEMAND_FILE = INPUT_DIR / "demand_competency_items_coded.csv"
OUTPUT_DIR = Path("供需匹配分析_规范技能百分比_中观边界强化")


def read_counts(path):
    counts = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            competency = (row.get("canonical_competency") or "").strip()
            if competency:
                counts[competency] += 1
    return counts


def pct(value, total):
    return value / total * 100 if total else 0.0


def classify_gap(gap_pp, supply_pct, demand_pct):
    if gap_pp >= 2.0:
        return "显著需求高于供给"
    if gap_pp >= 1.0:
        return "需求高于供给"
    if gap_pp <= -2.0:
        return "显著供给高于需求"
    if gap_pp <= -1.0:
        return "供给高于需求"
    if supply_pct < 0.2 and demand_pct < 0.2:
        return "低占比均衡"
    return "基本均衡"


def fmt(value):
    return f"{value:.2f}%"


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    supply_counts = read_counts(SUPPLY_FILE)
    demand_counts = read_counts(DEMAND_FILE)
    supply_total = sum(supply_counts.values())
    demand_total = sum(demand_counts.values())

    competencies = sorted(set(supply_counts) | set(demand_counts))
    rows = []
    for competency in competencies:
        s_pct = pct(supply_counts[competency], supply_total)
        d_pct = pct(demand_counts[competency], demand_total)
        gap_pp = d_pct - s_pct
        fit = min(s_pct, d_pct) / max(s_pct, d_pct) * 100 if max(s_pct, d_pct) else 100.0
        rows.append({
            "canonical_competency": competency,
            "supply_pct": fmt(s_pct),
            "demand_pct": fmt(d_pct),
            "demand_minus_supply_pp": f"{gap_pp:+.2f}",
            "relative_fit_pct": fmt(fit),
            "match_status": classify_gap(gap_pp, s_pct, d_pct),
        })

    rows.sort(key=lambda r: float(r["demand_minus_supply_pp"]), reverse=True)
    fields = [
        "canonical_competency",
        "supply_pct",
        "demand_pct",
        "demand_minus_supply_pp",
        "relative_fit_pct",
        "match_status",
    ]
    write_csv(OUTPUT_DIR / "competency_supply_demand_pct_match.csv", rows, fields)

    top_demand = rows[:12]
    top_supply = list(reversed(rows[-12:]))
    balanced = sorted(
        [r for r in rows if r["match_status"] in ("基本均衡", "低占比均衡")],
        key=lambda r: abs(float(r["demand_minus_supply_pp"])),
    )[:12]

    write_csv(OUTPUT_DIR / "top_demand_gap_pct.csv", top_demand, fields)
    write_csv(OUTPUT_DIR / "top_supply_excess_pct.csv", top_supply, fields)
    write_csv(OUTPUT_DIR / "balanced_competencies_pct.csv", balanced, fields)

    def md_table(table_rows):
        lines = [
            "| 规范技能 | 供给占比 | 需求占比 | 差值百分点 | 状态 |",
            "|---|---:|---:|---:|---|",
        ]
        for r in table_rows:
            lines.append(
                f"| {r['canonical_competency']} | {r['supply_pct']} | {r['demand_pct']} | "
                f"{r['demand_minus_supply_pp']} | {r['match_status']} |"
            )
        return "\n".join(lines)

    notes = f"""# 规范技能供需匹配分析（百分比口径）

本分析使用 `供需能力开放编码_中观边界强化口径_全量` 的 40 个规范技能。

## 计算口径

- 供给占比 = 该规范技能在供给端能力条目中的占比。
- 需求占比 = 该规范技能在需求端能力条目中的占比。
- 差值百分点 = 需求占比 - 供给占比。
- 正值表示需求端相对更强调，负值表示供给端相对更强调。
- 主表不使用绝对数量进行判断，避免两端规模差异干扰。

## 需求相对高于供给

{md_table(top_demand)}

## 供给相对高于需求

{md_table(top_supply)}

## 相对均衡能力

{md_table(balanced)}
"""
    (OUTPUT_DIR / "supply_demand_pct_match_summary.md").write_text(notes, encoding="utf-8")

    print(f"supply_total={supply_total}")
    print(f"demand_total={demand_total}")
    print(f"competencies={len(rows)}")
    print(f"output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
