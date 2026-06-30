#!/usr/bin/env python3
"""Draw a three-layer policy-demand-supply competency bridge figure."""

from __future__ import annotations

import csv
import math
import random
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Polygon


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "competency_three_layer_bridge_figure_package"
OUTPUT_STEM = OUTPUT_DIR / "competency_three_layer_bridge"


for font_name in [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "PingFang SC",
    "Hiragino Sans GB",
    "Arial Unicode MS",
]:
    try:
        fm.findfont(font_name, fallback_to_default=False)
        matplotlib.rcParams["font.family"] = [font_name, "sans-serif"]
        break
    except Exception:
        continue

matplotlib.rcParams.update(
    {
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "font.size": 7,
    }
)


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    x: float
    color: str
    keywords: tuple[str, ...]


THEMES = [
    Theme(
        "ship",
        "船舶海工",
        0.24,
        "#D95F4A",
        (
            "船舶",
            "船海",
            "海工装备",
            "海洋工程装备",
            "海工施工",
            "轮机",
            "船体",
            "焊接",
            "舾装",
            "修造",
            "质量检验",
        ),
    ),
    Theme(
        "port",
        "港航交通",
        0.34,
        "#59A14F",
        ("港", "航道", "航运", "通导", "海事", "水运", "物流", "供应链", "陆海联运"),
    ),
    Theme(
        "energy",
        "能源资源",
        0.44,
        "#4E79A7",
        ("能源", "风电", "海洋能", "深海", "油气", "矿产", "低碳", "碳汇", "资源开发"),
    ),
    Theme(
        "digital",
        "数字智能",
        0.54,
        "#8E6BBE",
        ("数智", "数据", "人工智能", "AI", "软件", "仿真", "建模", "电子", "控制", "通信", "水声", "信息系统"),
    ),
    Theme(
        "eco",
        "生态环境",
        0.64,
        "#2F9C95",
        ("环境", "生态", "海岸", "防灾", "观测", "测绘", "遥感", "气象", "地质", "海洋科学", "修复"),
    ),
    Theme(
        "bio",
        "水产生物",
        0.74,
        "#E28A3B",
        ("渔业", "水产", "养殖", "生物", "食品", "医药", "病害", "冷链"),
    ),
    Theme(
        "govern",
        "治理培养",
        0.84,
        "#7C8790",
        ("治理", "规划", "人才", "培养", "科研", "团队", "学习", "伦理", "法规", "金融", "平台", "成果", "科创"),
    ),
]

THEME_BY_KEY = {theme.key: theme for theme in THEMES}

LAYER_CONFIG = {
    "policy": {
        "title": "政策端",
        "subtitle": "战略任务 / 治理项目",
        "file": "competency_network_policy_figure_package/policy_network_node_metrics.csv",
        "edge_file": "competency_network_policy_figure_package/policy_network_edge_metrics.csv",
        "unit_field": "policy_file_count",
        "max_intralayer_edges": 16,
        "y": 0.735,
        "marker": "o",
        "edge": "#1f3b57",
        "fill": "#F3F7FB",
    },
    "demand": {
        "title": "需求端",
        "subtitle": "岗位任务 / 工程交付",
        "file": "competency_network_demand_figure_package/demand_network_node_metrics.csv",
        "edge_file": "competency_network_demand_figure_package/demand_network_edge_metrics.csv",
        "unit_field": "source_unit_count",
        "max_intralayer_edges": 18,
        "y": 0.50,
        "marker": "s",
        "edge": "#263238",
        "fill": "#F7F8FB",
    },
    "supply": {
        "title": "供给端",
        "subtitle": "课程训练 / 能力供给",
        "file": "competency_network_supply_figure_package/supply_network_node_metrics.csv",
        "edge_file": "competency_network_supply_figure_package/supply_network_edge_metrics.csv",
        "unit_field": "source_unit_count",
        "max_intralayer_edges": 16,
        "y": 0.265,
        "marker": "^",
        "edge": "#37474F",
        "fill": "#F8FAF5",
    },
}

CHAIN_ROLE_LABELS = {
    "policy": ("政策牵引", "政策任务与治理方向"),
    "demand": ("需求响应", "岗位任务与产业能力"),
    "supply": ("供给支撑", "课程训练与培养能力"),
}


DEMAND_DISPLAY = {
    "船舶建造项目生产管理能力": "船舶项目管理",
    "港口航道水运工程能力": "港航工程",
    "船舶制造工艺施工能力": "船舶制造施工",
    "海上风电工程能力": "海上风电",
    "船舶设计研发能力": "船舶设计研发",
    "船舶运营安全管理能力": "船舶运营安全",
    "仿真建模与现代工程工具能力": "仿真建模工具",
    "船舶质量检验检测能力": "船舶质量检测",
    "海洋工程项目建设管理能力": "海工项目管理",
    "船舶建造制造与质量能力": "船舶建造质量",
    "海洋工程装备设计制造能力": "海工装备制造",
    "港航物流与航运业务能力": "港航物流业务",
    "船舶修造维护与设备保障能力": "船舶修造维护",
    "海洋能源工程能力": "海洋能源工程",
    "人工智能与数据分析能力": "AI数据分析",
    "船舶焊接涂装装配能力": "船舶焊装涂装",
    "软件研发与信息系统能力": "软件信息系统",
    "低频跨域专业综合能力": "跨域综合",
    "船舶市场商务与供应链能力": "船舶商务供应链",
    "水声声学与海洋通信技术能力": "水声通信",
    "船舶电气自动化能力": "船舶电气",
    "船舶管系舾装工程能力": "船舶管系舾装",
    "水产养殖渔业技术能力": "水产养殖",
    "工程管理经济质量能力": "工程管理",
    "海洋环境监测评价治理能力": "海洋环境治理",
    "海洋调查观测测绘能力": "海洋观测测绘",
    "电子通信与自动控制能力": "电子通信控制",
    "船舶轮机动力能力": "船舶轮机",
    "海洋生物生态保育能力": "海洋生物生态",
    "海洋信息智能数据能力": "海洋智能数据",
    "团队沟通国际化能力": "团队沟通",
    "海洋文化场馆与科普服务能力": "海洋科普服务",
    "机械材料能源动力能力": "机械能源动力",
    "数字化工具与软件应用能力": "数字软件工具",
    "水产品加工质量与市场服务能力": "水产加工服务",
    "风电装备物流运输能力": "风电物流运输",
    "海事法律监管能力": "海事法律监管",
    "工程伦理安全可持续能力": "工程伦理安全",
    "船舶通导与智能系统能力": "船舶通导系统",
    "土木交通水利工程能力": "土木交通水利",
    "工程基础与问题分析能力": "工程问题分析",
    "海洋地质地球物理能力": "海洋地质物理",
    "科研实验创新实践能力": "科研实验实践",
    "物理海洋气象分析能力": "物理海洋气象",
    "航海驾驶与通导操作能力": "航海通导操作",
    "文献写作与教育教学能力": "文献教学",
    "环境工程治理能力": "环境工程治理",
}


MANUAL_LINKS = {
    ("policy", "demand"): [
        ("船舶海工制造能力", "船舶建造项目生产管理能力"),
        ("船舶海工制造能力", "船舶制造工艺施工能力"),
        ("船舶海工制造能力", "船舶设计研发能力"),
        ("海工装备制造能力", "海洋工程装备设计制造能力"),
        ("海工装备制造能力", "海洋工程项目建设管理能力"),
        ("港航工程建设能力", "港口航道水运工程能力"),
        ("港航物流服务能力", "港航物流与航运业务能力"),
        ("海上风电运维能力", "海上风电工程能力"),
        ("海洋能开发能力", "海洋能源工程能力"),
        ("深海资源开发能力", "海洋工程项目建设管理能力"),
        ("海洋数智平台能力", "人工智能与数据分析能力"),
        ("海洋数智平台能力", "软件研发与信息系统能力"),
        ("海洋数智平台能力", "仿真建模与现代工程工具能力"),
        ("海洋环境治理能力", "海洋环境监测评价治理能力"),
        ("海洋生态修复能力", "海洋生物生态保育能力"),
        ("海洋调查观测能力", "海洋调查观测测绘能力"),
        ("现代渔业能力", "水产养殖渔业技术能力"),
        ("水产加工冷链能力", "水产品加工质量与市场服务能力"),
        ("海洋生物生态能力", "海洋生物生态保育能力"),
        ("海洋生物医药能力", "海洋材料化学与生物医药能力"),
        ("海洋人才培养能力", "团队沟通国际化能力"),
    ],
    ("demand", "supply"): [
        ("船舶建造项目生产管理能力", "工程项目管理能力"),
        ("船舶建造项目生产管理能力", "船海工程基础能力"),
        ("船舶制造工艺施工能力", "船舶结构工艺能力"),
        ("船舶设计研发能力", "船舶总体设计能力"),
        ("船舶设计研发能力", "仿真建模能力"),
        ("船舶运营安全管理能力", "航海通导能力"),
        ("船舶运营安全管理能力", "船舶运营法规能力"),
        ("船舶质量检验检测能力", "工程伦理安全能力"),
        ("海上风电工程能力", "海洋能源工程能力"),
        ("海洋工程项目建设管理能力", "工程项目管理能力"),
        ("海洋工程项目建设管理能力", "海工施工运维能力"),
        ("海洋工程装备设计制造能力", "海工装备设计能力"),
        ("港口航道水运工程能力", "港航工程能力"),
        ("港航物流与航运业务能力", "港航物流能力"),
        ("人工智能与数据分析能力", "海洋数据分析能力"),
        ("仿真建模与现代工程工具能力", "仿真建模能力"),
        ("软件研发与信息系统能力", "软件开发能力"),
        ("水声声学与海洋通信技术能力", "水声通信能力"),
        ("海洋环境监测评价治理能力", "海洋环境修复能力"),
        ("海洋调查观测测绘能力", "海洋观测测绘能力"),
        ("水产养殖渔业技术能力", "水产养殖能力"),
        ("水产养殖渔业技术能力", "水产病害防控能力"),
        ("水产品加工质量与市场服务能力", "水产食品检验能力"),
        ("海洋生物生态保育能力", "海洋生物调查能力"),
        ("海洋生物生态保育能力", "海洋生物技术能力"),
        ("团队沟通国际化能力", "团队协作能力"),
        ("工程管理经济质量能力", "工程项目管理能力"),
        ("工程伦理安全可持续能力", "工程伦理安全能力"),
    ],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def display_label(side: str, label: str) -> str:
    if side == "demand":
        return DEMAND_DISPLAY.get(label, label.replace("能力", ""))
    return label.replace("能力", "")


def infer_theme(label: str, category: str) -> str:
    text = f"{label}{category}"
    if category in {"船舶工程", "工程装备"} and any(word in text for word in ("船舶", "海工", "装备")):
        return "ship"
    if category in {"港航交通"}:
        return "port"
    if category in {"海工能源", "资源能源"}:
        return "energy"
    if category in {"数字智能", "监测数据"}:
        return "digital"
    if category in {"海洋科学环境", "生态空间"}:
        return "eco"
    if category in {"水产生态食品", "生物渔业"}:
        return "bio"
    best_key = "govern"
    best_hits = 0
    for theme in THEMES:
        hits = sum(1 for kw in theme.keywords if kw in text)
        if hits > best_hits:
            best_key = theme.key
            best_hits = hits
    return best_key


def load_nodes() -> dict[str, list[dict[str, object]]]:
    nodes: dict[str, list[dict[str, object]]] = {}
    for side, config in LAYER_CONFIG.items():
        rows = read_csv(ROOT / config["file"])
        output = []
        for idx, row in enumerate(rows, start=1):
            label = row["cluster_label"].strip()
            category = row.get("category", "").strip()
            theme_key = infer_theme(label, category)
            output.append(
                {
                    "side": side,
                    "layer_title": config["title"],
                    "code": row.get("code", f"{side[0].upper()}{idx}"),
                    "label": label,
                    "display_label": display_label(side, label),
                    "category": category,
                    "theme": theme_key,
                    "item_count": int(row.get("item_count", 0) or 0),
                    "unit_count": int(row.get(config["unit_field"], 0) or 0),
                }
            )
        nodes[side] = output
    return nodes


def edge_weight(row: dict[str, str]) -> int:
    for field in [
        "cooccurrence_policy_files",
        "cooccurrence_source_units",
        "cooccurrence_units",
        "cooccurrence",
    ]:
        value = row.get(field, "")
        if value:
            try:
                return int(float(value))
            except ValueError:
                continue
    return 0


def edge_jaccard(row: dict[str, str]) -> float:
    try:
        return float(row.get("jaccard", 0) or 0)
    except ValueError:
        return 0.0


def load_intralayer_edges(
    nodes: dict[str, list[dict[str, object]]]
) -> list[dict[str, object]]:
    by_side_label = {
        side: {str(node["label"]): node for node in rows} for side, rows in nodes.items()
    }
    edges: list[dict[str, object]] = []
    for side, config in LAYER_CONFIG.items():
        path = ROOT / str(config["edge_file"])
        if not path.exists():
            continue
        selected: list[dict[str, object]] = []
        for row in read_csv(path):
            if row.get("in_backbone", "").strip().lower() != "yes":
                continue
            source_label = row.get("source", "").strip()
            target_label = row.get("target", "").strip()
            source = by_side_label[side].get(source_label)
            target = by_side_label[side].get(target_label)
            if not source or not target:
                continue
            source_theme = str(source["theme"])
            target_theme = str(target["theme"])
            selected.append(
                {
                    "side": side,
                    "source_label": source_label,
                    "target_label": target_label,
                    "source_display": source["display_label"],
                    "target_display": target["display_label"],
                    "theme": source_theme if source_theme == target_theme else "govern",
                    "weight": edge_weight(row),
                    "jaccard": edge_jaccard(row),
                }
            )
        selected.sort(key=lambda edge: (-int(edge["weight"]), -float(edge["jaccard"])))
        edges.extend(selected[: int(config.get("max_intralayer_edges", len(selected)))])
    return edges


def token_set(label: str) -> set[str]:
    cleaned = (
        label.replace("能力", "")
        .replace("与", "")
        .replace("及", "")
        .replace("和", "")
        .replace("现代", "")
    )
    tokens = {cleaned[i : i + 2] for i in range(max(len(cleaned) - 1, 0))}
    for word in [
        "船舶",
        "海工",
        "港航",
        "物流",
        "风电",
        "能源",
        "数据",
        "软件",
        "仿真",
        "环境",
        "生态",
        "水产",
        "生物",
        "工程",
        "管理",
        "科研",
    ]:
        if word in cleaned:
            tokens.add(word)
    return tokens


def similarity(a: dict[str, object], b: dict[str, object]) -> float:
    ta = token_set(str(a["label"])) | token_set(str(a["display_label"]))
    tb = token_set(str(b["label"])) | token_set(str(b["display_label"]))
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    theme_bonus = 0.22 if a["theme"] == b["theme"] else 0.0
    freq_bonus = 0.08 * math.sqrt(min(int(a["item_count"]), int(b["item_count"])) / 400)
    return jaccard + theme_bonus + freq_bonus


def build_manual_links(
    nodes: dict[str, list[dict[str, object]]]
) -> list[dict[str, object]]:
    by_side_label = {
        side: {str(node["label"]): node for node in rows} for side, rows in nodes.items()
    }
    links: list[dict[str, object]] = []
    for (source_side, target_side), pairs in MANUAL_LINKS.items():
        for source_label, target_label in pairs:
            source = by_side_label[source_side].get(source_label)
            target = by_side_label[target_side].get(target_label)
            if not source or not target:
                continue
            score = max(0.48, similarity(source, target) + 0.18)
            links.append(
                {
                    "source_side": source_side,
                    "target_side": target_side,
                    "source_label": source_label,
                    "target_label": target_label,
                    "source_display": source["display_label"],
                    "target_display": target["display_label"],
                    "theme": source["theme"] if source["theme"] == target["theme"] else target["theme"],
                    "score": score,
                    "link_type": "manual",
                }
            )
    return links


def build_candidate_links(nodes: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for source_side, target_side in [("policy", "demand"), ("demand", "supply")]:
        for source in nodes[source_side]:
            for target in nodes[target_side]:
                if source["theme"] != target["theme"]:
                    continue
                score = similarity(source, target)
                if score < 0.12:
                    continue
                candidates.append(
                    {
                        "source_side": source_side,
                        "target_side": target_side,
                        "source_label": source["label"],
                        "target_label": target["label"],
                        "source_display": source["display_label"],
                        "target_display": target["display_label"],
                        "theme": source["theme"],
                        "score": score,
                        "link_type": "rule",
                    }
                )
    return candidates


def compute_node_importance(
    nodes: dict[str, list[dict[str, object]]],
    intralayer_edges: list[dict[str, object]],
) -> dict[tuple[str, str], float]:
    max_items = {
        side: max(int(node["item_count"]) for node in rows) or 1
        for side, rows in nodes.items()
    }
    degree: Counter[tuple[str, str]] = Counter()
    weighted_degree: Counter[tuple[str, str]] = Counter()
    for edge in intralayer_edges:
        side = str(edge["side"])
        source = (side, str(edge["source_label"]))
        target = (side, str(edge["target_label"]))
        weight = max(int(edge["weight"]), 1)
        degree[source] += 1
        degree[target] += 1
        weighted_degree[source] += int(math.sqrt(weight))
        weighted_degree[target] += int(math.sqrt(weight))
    max_degree = {
        side: max(
            [degree[(side, str(node["label"]))] for node in rows] + [1]
        )
        for side, rows in nodes.items()
    }
    max_weighted = {
        side: max(
            [weighted_degree[(side, str(node["label"]))] for node in rows] + [1]
        )
        for side, rows in nodes.items()
    }
    importance: dict[tuple[str, str], float] = {}
    for side, rows in nodes.items():
        for node in rows:
            key = (side, str(node["label"]))
            item_score = math.sqrt(int(node["item_count"]) / max_items[side])
            degree_score = degree[key] / max_degree[side]
            weighted_score = weighted_degree[key] / max_weighted[side]
            importance[key] = 0.58 * item_score + 0.24 * degree_score + 0.18 * weighted_score
    return importance


def prioritized_link_score(
    link: dict[str, object],
    importance: dict[tuple[str, str], float],
) -> float:
    source_key = (str(link["source_side"]), str(link["source_label"]))
    target_key = (str(link["target_side"]), str(link["target_label"]))
    semantic_score = float(link["score"])
    source_importance = importance.get(source_key, 0)
    target_importance = importance.get(target_key, 0)
    manual_bonus = 0.03 if link["link_type"] == "manual" else 0.0
    exact_name_penalty = 0.22 if str(link["source_display"]) == str(link["target_display"]) else 0.0
    return (
        0.95 * source_importance
        + 0.95 * target_importance
        + 0.18 * semantic_score
        + manual_bonus
        - exact_name_penalty
    )


def select_links(
    nodes: dict[str, list[dict[str, object]]],
    intralayer_edges: list[dict[str, object]],
) -> list[dict[str, object]]:
    importance = compute_node_importance(nodes, intralayer_edges)
    manual = build_manual_links(nodes)
    candidate = build_candidate_links(nodes)
    seen = {(l["source_side"], l["target_side"], l["source_label"], l["target_label"]) for l in manual}
    combined = manual + [
        link
        for link in sorted(candidate, key=lambda x: (-float(x["score"]), str(x["source_label"])))
        if (link["source_side"], link["target_side"], link["source_label"], link["target_label"]) not in seen
    ]

    selected: list[dict[str, object]] = []
    pair_counts: Counter[tuple[str, str]] = Counter()
    node_degree: Counter[tuple[str, str]] = Counter()
    theme_pair_count: Counter[tuple[str, str, str]] = Counter()
    for link in combined:
        link["priority_score"] = prioritized_link_score(link, importance)
        link["source_importance"] = importance.get(
            (str(link["source_side"]), str(link["source_label"])), 0
        )
        link["target_importance"] = importance.get(
            (str(link["target_side"]), str(link["target_label"])), 0
        )
        link["semantic_score"] = float(link["score"])

    for link in sorted(combined, key=lambda x: -float(x["priority_score"])):
        pair = (str(link["source_side"]), str(link["target_side"]))
        source_node = (str(link["source_side"]), str(link["source_label"]))
        target_node = (str(link["target_side"]), str(link["target_label"]))
        theme_pair = (pair[0], pair[1], str(link["theme"]))
        if pair_counts[pair] >= 8:
            continue
        if node_degree[source_node] >= 3 or node_degree[target_node] >= 3:
            continue
        if theme_pair_count[theme_pair] >= 3:
            continue
        selected.append(link)
        pair_counts[pair] += 1
        node_degree[source_node] += 1
        node_degree[target_node] += 1
        theme_pair_count[theme_pair] += 1
    return selected


def theme_horizontal_bounds() -> dict[str, tuple[float, float]]:
    bounds: dict[str, tuple[float, float]] = {}
    for idx, theme in enumerate(THEMES):
        if idx == 0:
            left = 0.115
        else:
            left = (THEMES[idx - 1].x + theme.x) / 2
        if idx == len(THEMES) - 1:
            right = 0.900
        else:
            right = (theme.x + THEMES[idx + 1].x) / 2
        bounds[theme.key] = (left + 0.010, right - 0.010)
    return bounds


def grid_position(
    idx: int,
    count: int,
    x_left: float,
    x_right: float,
    y_center: float,
    y_span: float,
    rng: random.Random,
) -> tuple[float, float]:
    if count <= 1:
        return ((x_left + x_right) / 2, y_center)
    rows = min(4, max(2, math.ceil(math.sqrt(count * 0.72))))
    cols = math.ceil(count / rows)
    row = idx % rows
    col = idx // rows
    if cols <= 1:
        x = (x_left + x_right) / 2
    else:
        x = x_left + (col + 0.5) * (x_right - x_left) / cols
    if rows <= 1:
        y = y_center
    else:
        y_top = y_center + y_span / 2
        y_bottom = y_center - y_span / 2
        y = y_top - (row + 0.5) * y_span / rows
    if col % 2:
        y += y_span / (rows * 7)
    x += rng.uniform(-0.004, 0.004)
    y += rng.uniform(-0.004, 0.004)
    return x, y


def assign_positions(nodes: dict[str, list[dict[str, object]]]) -> dict[tuple[str, str], tuple[float, float]]:
    rng = random.Random(73)
    positions: dict[tuple[str, str], tuple[float, float]] = {}
    layer_height = 0.158
    x_left, x_right = 0.125, 0.905
    min_distance = 0.034
    for side, rows in nodes.items():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for node in rows:
            grouped[str(node["theme"])].append(node)
        theme_keys = [theme.key for theme in THEMES if theme.key in grouped]
        weights = {
            theme_key: max(0.8, math.sqrt(len(grouped[theme_key])))
            for theme_key in theme_keys
        }
        total_weight = sum(weights.values()) or 1
        gap = 0.012
        usable_width = (x_right - x_left) - gap * (len(theme_keys) - 1)
        theme_bounds: dict[str, tuple[float, float]] = {}
        cursor = x_left
        for theme_key in theme_keys:
            width = usable_width * weights[theme_key] / total_weight
            theme_bounds[theme_key] = (cursor, cursor + width)
            cursor += width + gap

        placed: list[tuple[tuple[str, str], float, float, str]] = []
        y_center = float(LAYER_CONFIG[side]["y"])
        y_low = y_center - layer_height / 2
        y_high = y_center + layer_height / 2
        for theme_key in theme_keys:
            theme_nodes = sorted(
                grouped[theme_key],
                key=lambda node: (-int(node["item_count"]), str(node["label"])),
            )
            band_left, band_right = theme_bounds[theme_key]
            band_center = (band_left + band_right) / 2
            band_width = band_right - band_left
            local_min_distance = max(0.029, min_distance - 0.0015 * max(0, len(theme_nodes) - 8))
            for node in theme_nodes:
                key = (side, str(node["label"]))
                ideal_x = band_center
                best_candidate = None
                best_score = -999.0
                for attempt in range(900):
                    if attempt < 650:
                        x = rng.gauss(ideal_x, max(band_width / 4.6, 0.018))
                    else:
                        x = rng.uniform(band_left, band_right)
                    y = rng.uniform(y_low, y_high)
                    x = max(band_left, min(band_right, x))
                    if placed:
                        nearest = min(math.hypot(x - px, y - py) for _, px, py, _ in placed)
                    else:
                        nearest = 1.0
                    same_theme_nearest = min(
                        [math.hypot(x - px, y - py) for _, px, py, ptheme in placed if ptheme == theme_key] or [1.0]
                    )
                    score = nearest + 0.18 * same_theme_nearest - 0.05 * abs(x - ideal_x) + rng.uniform(0, 0.006)
                    if nearest >= local_min_distance:
                        best_candidate = (x, y)
                        break
                    if score > best_score:
                        best_candidate = (x, y)
                        best_score = score
                x, y = best_candidate if best_candidate else (ideal_x, y_center)
                positions[key] = (x, y)
                placed.append((key, x, y, theme_key))

        for _ in range(120):
            moved = False
            keys = [key for key, _, _, _ in placed]
            theme_by_key = {key: theme for key, _, _, theme in placed}
            bounds_by_key = {key: theme_bounds[theme] for key, theme in theme_by_key.items()}
            for i, key_a in enumerate(keys):
                ax_, ay = positions[key_a]
                for key_b in keys[i + 1 :]:
                    bx, by = positions[key_b]
                    dx = ax_ - bx
                    dy = ay - by
                    dist = math.hypot(dx, dy)
                    if dist >= min_distance:
                        continue
                    if dist < 1e-6:
                        dx = rng.uniform(-0.001, 0.001)
                        dy = rng.uniform(-0.001, 0.001)
                        dist = math.hypot(dx, dy)
                    push = (min_distance - dist) / 2
                    ux = dx / dist
                    uy = dy / dist
                    a_left, a_right = bounds_by_key[key_a]
                    b_left, b_right = bounds_by_key[key_b]
                    ax_ = max(a_left, min(a_right, ax_ + ux * push))
                    ay = max(y_low, min(y_high, ay + uy * push))
                    bx = max(b_left, min(b_right, bx - ux * push))
                    by = max(y_low, min(y_high, by - uy * push))
                    positions[key_a] = (ax_, ay)
                    positions[key_b] = (bx, by)
                    moved = True
            if not moved:
                break
    return positions


def size_for_count(count: int, max_count: int) -> float:
    return 18 + 240 * math.sqrt(count / max_count)


def wrap_label(text: str, width: int = 7) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=True))


def label_nodes(
    nodes: dict[str, list[dict[str, object]]],
    links: list[dict[str, object]],
    intralayer_edges: list[dict[str, object]],
) -> set[tuple[str, str]]:
    label_score: Counter[tuple[str, str]] = Counter()
    for link in links:
        label_score[(str(link["source_side"]), str(link["source_label"]))] += 5
        label_score[(str(link["target_side"]), str(link["target_label"]))] += 5

    for side, rows in nodes.items():
        max_count = max(int(node["item_count"]) for node in rows) or 1
        for node in rows:
            key = (side, str(node["label"]))
            label_score[key] += 3 * math.sqrt(int(node["item_count"]) / max_count)

    degree: Counter[tuple[str, str]] = Counter()
    for edge in intralayer_edges:
        degree[(str(edge["side"]), str(edge["source_label"]))] += 1
        degree[(str(edge["side"]), str(edge["target_label"]))] += 1
    for key, value in degree.items():
        label_score[key] += 1.4 * value

    selected: set[tuple[str, str]] = set()
    for side in nodes:
        candidates = [(key, score) for key, score in label_score.items() if key[0] == side]
        for key, _ in sorted(candidates, key=lambda item: (-item[1], item[0][1]))[:9]:
            selected.add(key)
    return selected


def draw_layer_frames(ax) -> None:
    x0, x1 = 0.055, 0.945
    height = 0.22
    skew = 0.040
    for side, cfg in LAYER_CONFIG.items():
        y = float(cfg["y"])
        points = [
            (x0 + skew, y + height / 2),
            (x1 + skew, y + height / 2),
            (x1 - skew, y - height / 2),
            (x0 - skew, y - height / 2),
        ]
        polygon = Polygon(
            points,
            closed=True,
            facecolor=str(cfg["fill"]),
            edgecolor="#425466",
            linewidth=1.2,
            alpha=0.72,
            zorder=0,
        )
        ax.add_patch(polygon)


def draw_chain_role_labels(ax) -> None:
    for side, cfg in LAYER_CONFIG.items():
        title, subtitle = CHAIN_ROLE_LABELS[side]
        y = float(cfg["y"])
        ax.text(
            0.078,
            y + 0.073,
            title,
            ha="left",
            va="center",
            fontsize=8.4,
            fontweight="bold",
            color="#203246",
            zorder=4,
        )
        ax.text(
            0.078,
            y + 0.048,
            subtitle,
            ha="left",
            va="center",
            fontsize=5.6,
            color="#5A6672",
            zorder=4,
        )


def draw_theme_guides(ax) -> None:
    for theme in THEMES:
        ax.text(
            theme.x,
            0.905,
            theme.label,
            ha="center",
            va="center",
            fontsize=8.2,
            fontweight="bold",
            color=theme.color,
        )
        ax.plot(
            [theme.x, theme.x],
            [0.16, 0.86],
            color=theme.color,
            lw=0.45,
            alpha=0.12,
            zorder=0,
        )


def draw_intralayer_edges(ax, intralayer_edges, positions) -> None:
    if not intralayer_edges:
        return
    max_weight = max(int(edge["weight"]) for edge in intralayer_edges) or 1
    for edge in sorted(intralayer_edges, key=lambda item: int(item["weight"])):
        start = positions.get((str(edge["side"]), str(edge["source_label"])))
        end = positions.get((str(edge["side"]), str(edge["target_label"])))
        if not start or not end:
            continue
        theme = THEME_BY_KEY[str(edge["theme"])]
        strength = math.sqrt(int(edge["weight"]) / max_weight)
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=theme.color,
            alpha=0.18 + 0.28 * strength,
            lw=0.55 + 1.25 * strength,
            linestyle="-",
            solid_capstyle="round",
            zorder=1,
        )


def draw_links(ax, links, positions) -> None:
    for link in sorted(links, key=lambda x: float(x["score"])):
        start = positions.get((str(link["source_side"]), str(link["source_label"])))
        end = positions.get((str(link["target_side"]), str(link["target_label"])))
        if not start or not end:
            continue
        theme = THEME_BY_KEY[str(link["theme"])]
        score = float(link["score"])
        width = 0.80 + 2.60 * min(score, 0.85)
        arrow = FancyArrowPatch(
            (start[0], start[1]),
            (end[0], end[1]),
            arrowstyle="-|>",
            mutation_scale=7.2,
            shrinkA=5.5,
            shrinkB=7.2,
            linestyle=(0, (4, 4)),
            color=theme.color,
            alpha=0.30 + 0.42 * min(score, 0.85),
            linewidth=width,
            zorder=2,
        )
        ax.add_patch(arrow)


def draw_nodes(ax, nodes, positions, links, intralayer_edges) -> None:
    max_count_by_side = {
        side: max(int(node["item_count"]) for node in rows) or 1
        for side, rows in nodes.items()
    }
    labels = label_nodes(nodes, links, intralayer_edges)
    label_offsets = {"policy": 0.024, "demand": 0.020, "supply": -0.025}
    for side, rows in nodes.items():
        cfg = LAYER_CONFIG[side]
        for node in rows:
            x, y = positions[(side, str(node["label"]))]
            theme = THEME_BY_KEY[str(node["theme"])]
            size = size_for_count(int(node["item_count"]), max_count_by_side[side])
            ax.scatter(
                x,
                y,
                s=size,
                marker=str(cfg["marker"]),
                facecolor=theme.color,
                edgecolor=str(cfg["edge"]),
                linewidth=0.75,
                alpha=0.94,
                zorder=3,
            )
            if (side, str(node["label"])) in labels:
                dy = label_offsets[side]
                va = "bottom" if dy > 0 else "top"
                ax.text(
                    x,
                    y + dy,
                    wrap_label(str(node["display_label"]), 7),
                    ha="center",
                    va=va,
                    fontsize=5.2,
                    color="#18242F",
                    linespacing=1.03,
                    bbox=dict(
                        boxstyle="round,pad=0.10,rounding_size=0.03",
                        facecolor="white",
                        edgecolor="none",
                        alpha=0.73,
                    ),
                    zorder=5,
                    path_effects=[pe.withStroke(linewidth=0.6, foreground="white", alpha=0.9)],
                )


def draw_side_notes(ax) -> None:
    notes = [
        ("政策端", "政策任务提出能力方向\n偏治理、产业和平台建设"),
        ("需求端", "岗位记录体现任务链条\n偏工程交付和生产组织"),
        ("供给端", "培养方案提供课程训练\n偏基础、实践和通用素养"),
    ]
    y_positions = [0.76, 0.50, 0.24]
    for (title, text), y in zip(notes, y_positions):
        ax.text(0.025, y + 0.058, f"• {title}", ha="left", va="top", fontsize=9.3, fontweight="bold", color="#1f3b57")
        ax.text(0.040, y + 0.022, text, ha="left", va="top", fontsize=7.4, color="#263238", linespacing=1.4)


def draw_legend(ax, links) -> None:
    ax.text(0.905, 0.805, "图例", fontsize=9.6, fontweight="bold", color="#172532")
    ax.plot([0.905, 0.955], [0.755, 0.755], color="#52606D", lw=1.7, linestyle=(0, (4, 4)), alpha=0.62)
    ax.text(0.965, 0.755, "核心跨层关联", va="center", fontsize=7.0, color="#263238")
    ax.scatter(0.914, 0.710, s=62, marker="o", color="#B8C0C7", edgecolor="#263238", linewidth=0.5)
    ax.text(0.935, 0.710, "政策端", va="center", fontsize=7.0, color="#263238")
    ax.scatter(0.914, 0.675, s=62, marker="s", color="#B8C0C7", edgecolor="#263238", linewidth=0.5)
    ax.text(0.935, 0.675, "需求端", va="center", fontsize=7.0, color="#263238")
    ax.scatter(0.914, 0.640, s=72, marker="^", color="#B8C0C7", edgecolor="#263238", linewidth=0.5)
    ax.text(0.935, 0.640, "供给端", va="center", fontsize=7.0, color="#263238")
    pair_counts = Counter((link["source_side"], link["target_side"]) for link in links)
    ax.text(
        0.905,
        0.590,
        f"虚线：政策-需求 {pair_counts[('policy', 'demand')]} 条\n需求-供给 {pair_counts[('demand', 'supply')]} 条",
        ha="left",
        va="top",
        fontsize=6.7,
        color="#52606D",
        linespacing=1.35,
    )


SIDE_NAMES = {
    "policy": "政策端",
    "demand": "需求端",
    "supply": "供给端",
}


def clean_md_cell(value: object) -> str:
    return str(value).replace("|", "/").replace("\n", " ")


def markdown_table(
    headers: list[str],
    rows: list[list[object]],
    empty_message: str = "暂无连续贯通链条。",
) -> str:
    if not rows:
        return empty_message
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean_md_cell(value) for value in row) + " |")
    return "\n".join(lines)


def build_chain_paths(links: list[dict[str, object]]) -> list[dict[str, object]]:
    policy_to_demand = [
        link
        for link in links
        if link["source_side"] == "policy" and link["target_side"] == "demand"
    ]
    demand_to_supply: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for link in links:
        if link["source_side"] == "demand" and link["target_side"] == "supply":
            demand_to_supply[str(link["source_label"])].append(link)

    chains: list[dict[str, object]] = []
    for upper in policy_to_demand:
        for lower in demand_to_supply.get(str(upper["target_label"]), []):
            chains.append(
                {
                    "policy_label": upper["source_label"],
                    "demand_label": upper["target_label"],
                    "supply_label": lower["target_label"],
                    "policy_display": upper["source_display"],
                    "demand_display": upper["target_display"],
                    "supply_display": lower["target_display"],
                    "policy_to_demand_theme": THEME_BY_KEY[str(upper["theme"])].label,
                    "demand_to_supply_theme": THEME_BY_KEY[str(lower["theme"])].label,
                    "chain_score": (
                        float(upper["priority_score"]) + float(lower["priority_score"])
                    )
                    / 2,
                }
            )
    chains.sort(key=lambda row: -float(row["chain_score"]))
    return chains


def build_link_table(links: list[dict[str, object]], source_side: str) -> str:
    rows = []
    for link in sorted(
        [item for item in links if item["source_side"] == source_side],
        key=lambda item: -float(item["priority_score"]),
    ):
        rows.append(
            [
                link["source_display"],
                link["target_display"],
                THEME_BY_KEY[str(link["theme"])].label,
                f"{float(link['source_importance']):.2f}",
                f"{float(link['target_importance']):.2f}",
                f"{float(link['priority_score']):.2f}",
            ]
        )
    return markdown_table(
        ["上层节点", "下层节点", "主题", "上层重要性", "下层重要性", "优先级"],
        rows,
    )


def build_chain_table(chains: list[dict[str, object]]) -> str:
    rows = [
        [
            chain["policy_display"],
            chain["demand_display"],
            chain["supply_display"],
            chain["policy_to_demand_theme"],
            chain["demand_to_supply_theme"],
            f"{float(chain['chain_score']):.2f}",
        ]
        for chain in chains
    ]
    return markdown_table(
        ["政策牵引", "需求响应", "供给支撑", "政策-需求主题", "需求-供给主题", "链条强度"],
        rows,
    )


def build_uncontinued_policy_table(links: list[dict[str, object]]) -> str:
    demand_sources = {
        str(link["source_label"])
        for link in links
        if link["source_side"] == "demand" and link["target_side"] == "supply"
    }
    rows = []
    for link in sorted(
        [item for item in links if item["source_side"] == "policy"],
        key=lambda item: -float(item["priority_score"]),
    ):
        if str(link["target_label"]) in demand_sources:
            continue
        rows.append(
            [
                link["source_display"],
                link["target_display"],
                THEME_BY_KEY[str(link["theme"])].label,
                f"{float(link['priority_score']):.2f}",
            ]
        )
    return markdown_table(
        ["政策端节点", "需求端节点", "主题", "连接优先级"],
        rows,
        "当前保留的核心关系中，政策端到需求端的连接均继续向供给端贯通。",
    )


def build_unrooted_demand_supply_table(links: list[dict[str, object]]) -> str:
    demand_targets = {
        str(link["target_label"])
        for link in links
        if link["source_side"] == "policy" and link["target_side"] == "demand"
    }
    rows = []
    for link in sorted(
        [item for item in links if item["source_side"] == "demand"],
        key=lambda item: -float(item["priority_score"]),
    ):
        if str(link["source_label"]) in demand_targets:
            continue
        rows.append(
            [
                link["source_display"],
                link["target_display"],
                THEME_BY_KEY[str(link["theme"])].label,
                f"{float(link['priority_score']):.2f}",
            ]
        )
    return markdown_table(
        ["需求端节点", "供给端节点", "主题", "连接优先级"],
        rows,
        "当前保留的核心关系中，需求端到供给端的连接均存在政策端上游牵引。",
    )


def build_bridge_document(
    nodes: dict[str, list[dict[str, object]]],
    links: list[dict[str, object]],
    intralayer_edges: list[dict[str, object]],
    chains: list[dict[str, object]],
) -> str:
    policy_demand_count = sum(1 for link in links if link["source_side"] == "policy")
    demand_supply_count = sum(1 for link in links if link["source_side"] == "demand")
    edge_counts = Counter(str(edge["side"]) for edge in intralayer_edges)
    chain_text = build_chain_table(chains)
    policy_demand_table = build_link_table(links, "policy")
    demand_supply_table = build_link_table(links, "demand")
    uncontinued_policy_table = build_uncontinued_policy_table(links)
    unrooted_demand_supply_table = build_unrooted_demand_supply_table(links)
    strongest_chain = chains[0] if chains else None
    strongest_chain_text = (
        f"{strongest_chain['policy_display']} -> {strongest_chain['demand_display']} -> {strongest_chain['supply_display']}"
        if strongest_chain
        else "当前核心关系中未形成完整三层贯通链条"
    )
    return f"""# 政策-需求-供给能力传导链说明

![政策-需求-供给能力传导链](competency_three_layer_bridge.png)

## 一、整幅图的含义

这幅图用来说明海洋人才能力体系中“政策牵引—需求响应—供给支撑”的传导关系。上层为政策端，表示政策文本中提出的产业方向、治理任务、工程项目和平台建设要求；中层为需求端，表示招聘岗位中体现的技术任务、工程交付、生产组织和管理能力；下层为供给端，表示高校培养方案、课程体系和实践训练中提供的能力支撑。

图中节点表示规范化后的中观能力，节点越大表示该能力在对应数据源中出现频次越高；节点颜色表示能力主题，包括船舶海工、港航交通、能源资源、数字智能、生态环境、水产生物和治理培养。层内实线表示同一端内部的能力共现关系，跨层虚线箭头表示上层能力任务向下层能力需求或能力供给的传导关系。整幅图的重点不是展示所有能力，而是识别政策、市场和培养体系之间是否形成了连续的能力链条。

## 二、层内连接如何确定

层内连接用于刻画同一数据源内部的能力组合关系。也就是说，政策端内部的线表示政策文本中哪些能力经常一起出现，需求端内部的线表示招聘岗位中哪些能力经常被同时要求，供给端内部的线表示培养方案或课程体系中哪些能力经常被共同训练。

具体处理规则如下：

- 政策端层内连接：若两个能力在同一政策文件中共同出现，则形成候选共现关系；共现强度由共同出现的政策文件数表示，即 `cooccurrence_policy_files`。
- 需求端层内连接：若两个能力在同一招聘来源单元中共同出现，则形成候选共现关系；共现强度由共同出现的来源单元数表示，即 `cooccurrence_source_units`。
- 供给端层内连接：若两个能力在同一培养方案、课程或来源单元中共同出现，则形成候选共现关系；共现强度同样由 `cooccurrence_source_units` 表示。
- 每条候选边同时计算 Jaccard 系数，用于衡量两个能力共现关系相对于各自出现范围的相对紧密程度。
- 图中只保留各端能力网络中的骨干边，即原始边表中 `in_backbone = yes` 的关系；在骨干边内部，再按共现强度和 Jaccard 系数排序，保留最核心的层内连接。

当前图中共保留层内实线 {len(intralayer_edges)} 条，其中政策端 {edge_counts['policy']} 条，需求端 {edge_counts['demand']} 条，供给端 {edge_counts['supply']} 条。层内连接不表示因果关系，而表示同一端内部较稳定的能力组合。例如，若两个能力在多个政策文件或多个岗位中反复共同出现，说明它们构成了该端能力体系中的一个重要组合。

## 三、层间连接如何确定

层间连接用于识别“政策任务—岗位需求—培养供给”的能力传导关系。本文不把名称完全相同作为主要连接依据，因为政策文本、招聘文本和培养方案的表达方式不同，同一类能力往往会以不同名称出现。跨层连接强调的是功能承接关系，即上层提出的任务是否能够在下层找到相应的岗位需求或培养支撑。

跨层连接按以下步骤确定：

1. 只连接相邻层。政策端只连接需求端，需求端只连接供给端，不直接连接政策端和供给端。这样可以保留“政策先进入岗位需求，再由培养体系承接”的中介逻辑。
2. 生成候选关系。规则候选关系要求上下层节点属于同一能力主题，并且具有一定语义相近度。语义相近度由能力名称的词片段重合、主题一致性和频次信息共同构成；少量人工校准关系用于保留功能上明确承接、但主题短名可能不同的关系。
3. 计算节点重要性。节点重要性由出现频次、层内连接度和层内加权连接强度共同确定：

```text
节点重要性 = 0.58 × 归一化出现频次
          + 0.24 × 层内连接度
          + 0.18 × 层内加权连接强度
```

4. 计算跨层连接优先级。跨层关系不是单纯按语义相似排序，而是更强调上下层节点本身是否重要：

```text
跨层优先级 = 0.95 × 上层节点重要性
          + 0.95 × 下层节点重要性
          + 0.18 × 语义相近度
          + 少量人工校准关系加成
          - 同名关系惩罚
```

5. 控制图面复杂度。每组相邻层最多保留 8 条跨层关系，单个节点最多参与 3 条跨层关系，同一主题在同一层间最多保留 3 条关系。这样做是为了突出关键传导关系，而不是把所有可能关系都画出来。

当前图中共保留跨层虚线箭头 {len(links)} 条，其中政策端到需求端 {policy_demand_count} 条，需求端到供给端 {demand_supply_count} 条。需要强调的是，虚线箭头表示“能力传导或承接”，不表示两个节点名称相同，也不表示已经存在严格因果关系。

## 四、从图中得到的主要结果

第一，政策、需求和供给之间并不是均匀贯通的关系，而是只在部分能力主题上形成较清晰的传导链。当前图中识别出 {len(chains)} 条三层贯通链条，即同一个需求端节点既承接了政策端任务，又继续连接到供给端能力。强度最高的贯通链条为：{strongest_chain_text}。这说明船舶海工、港航工程和工程项目组织类能力在政策牵引、岗位需求和培养供给之间具有较强连续性。

第二，船舶海工相关链条最完整。政策端的“港航工程建设”和“船舶海工制造”能够向需求端的“船舶项目管理”“船舶制造施工”等节点传导，并进一步连接到供给端的“船舶轮机”“工程项目管理”等能力。这表明传统工程建设、船舶制造和项目管理类能力已经形成比较明确的政策—需求—供给承接路径。

第三，数字智能方向也形成了较清晰的传导链。政策端的“海洋数智平台”连接到需求端的“仿真建模工具”，并继续连接到供给端的“软件开发”和“海洋数据分析”。这表明海洋领域数字化平台建设正在转化为岗位中的工具使用、建模仿真和数据处理能力需求，培养端也已经提供一定的课程和训练支撑。

第四，部分政策需求尚未在供给端形成核心贯通。现代渔业、港航物流等政策或产业需求虽然能够连接到需求端，但在当前保留的核心跨层关系中没有继续向供给端贯通。这不表示供给端完全没有相关课程，而是说明在当前阈值和核心网络口径下，这些方向的培养支撑关系不如船舶海工和数字智能方向突出。

第五，部分供给能力能够支撑岗位需求，但其政策上游牵引在核心链条中不够明显。例如“科研实践”“工程伦理安全”“船舶轮机”等供给端能力与需求端存在连接，但其中部分关系没有在当前核心图中形成完整的政策端上游链条。这提示供给端存在一定的通用能力和专业基础能力，但这些能力与政策任务之间的显性对应关系仍有进一步强化空间。

## 五、三层贯通链条

下表列出当前图中能够从政策端连续传导到供给端的能力链条。这些链条可以理解为政策目标、岗位能力需求和高校培养供给之间相对完整的承接路径。

{chain_text}

## 六、未继续贯通的关系

### 已传导到需求端、但未继续连接到供给端

{uncontinued_policy_table}

### 已由供给端支撑、但缺少政策端上游连接

{unrooted_demand_supply_table}

## 七、跨层连接明细

### 政策端到需求端：政策任务向岗位能力需求转化

{policy_demand_table}

### 需求端到供给端：岗位能力需求向培养训练体系承接

{demand_supply_table}

## 八、可用于论文的表述

本文构建了政策端、需求端和供给端三层能力传导网络，用以分析海洋人才能力体系中政策牵引、产业需求和培养供给之间的衔接关系。层内连接依据同一数据源内部的能力共现关系确定，用于刻画政策文本、招聘岗位和培养方案各自内部的能力组合结构；层间连接依据主题一致性、语义相近性、节点出现频次和层内网络地位共同确定，用于识别政策任务向岗位需求、岗位需求向培养供给的潜在传导路径。结果显示，船舶海工和数字智能方向形成了较清晰的政策—需求—供给贯通链条，而现代渔业、港航物流等方向在当前核心网络中更多停留在政策—需求层面，提示部分政策导向与培养供给之间仍存在结构性衔接不足。

## 九、建议图注

图 X 政策端、需求端与供给端的海洋人才能力传导链。上、中、下三层分别表示政策牵引、产业需求响应和人才供给支撑。节点表示规范化后的中观能力，节点大小表示能力出现频次，节点颜色表示能力主题。层内实线表示同一数据源内部基于共现关系识别出的能力组合，跨层虚线箭头表示基于主题一致性、语义相近性和节点重要性识别出的能力传导关系。虚线箭头不代表能力名称完全一致，而表示政策任务、岗位需求与培养能力之间的潜在承接路径。
"""


def write_outputs(nodes, links, positions, intralayer_edges) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    node_fields = [
        "side",
        "code",
        "cluster_label",
        "display_label",
        "category",
        "theme",
        "item_count",
        "unit_count",
        "x",
        "y",
    ]
    with (OUTPUT_DIR / "three_layer_node_metrics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=node_fields)
        writer.writeheader()
        for side, rows in nodes.items():
            for node in rows:
                x, y = positions[(side, str(node["label"]))]
                writer.writerow(
                    {
                        "side": side,
                        "code": node["code"],
                        "cluster_label": node["label"],
                        "display_label": node["display_label"],
                        "category": node["category"],
                        "theme": THEME_BY_KEY[str(node["theme"])].label,
                        "item_count": node["item_count"],
                        "unit_count": node["unit_count"],
                        "x": f"{x:.6f}",
                        "y": f"{y:.6f}",
                    }
                )
    link_fields = [
        "source_side",
        "target_side",
        "source_label",
        "target_label",
        "source_display",
        "target_display",
        "theme",
        "score",
        "semantic_score",
        "source_importance",
        "target_importance",
        "priority_score",
        "link_type",
    ]
    with (OUTPUT_DIR / "three_layer_interlayer_links.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=link_fields)
        writer.writeheader()
        for link in links:
            row = dict(link)
            row["theme"] = THEME_BY_KEY[str(link["theme"])].label
            row["score"] = f"{float(link['score']):.6f}"
            row["semantic_score"] = f"{float(link['semantic_score']):.6f}"
            row["source_importance"] = f"{float(link['source_importance']):.6f}"
            row["target_importance"] = f"{float(link['target_importance']):.6f}"
            row["priority_score"] = f"{float(link['priority_score']):.6f}"
            writer.writerow(row)
    intralayer_fields = [
        "side",
        "source_label",
        "target_label",
        "source_display",
        "target_display",
        "theme",
        "weight",
        "jaccard",
    ]
    with (OUTPUT_DIR / "three_layer_intralayer_edges.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=intralayer_fields)
        writer.writeheader()
        for edge in intralayer_edges:
            row = dict(edge)
            row["theme"] = THEME_BY_KEY[str(edge["theme"])].label
            row["jaccard"] = f"{float(edge['jaccard']):.6f}"
            writer.writerow(row)

    chains = build_chain_paths(links)
    chain_fields = [
        "policy_label",
        "demand_label",
        "supply_label",
        "policy_display",
        "demand_display",
        "supply_display",
        "policy_to_demand_theme",
        "demand_to_supply_theme",
        "chain_score",
    ]
    with (OUTPUT_DIR / "three_layer_chain_paths.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=chain_fields)
        writer.writeheader()
        for chain in chains:
            row = dict(chain)
            row["chain_score"] = f"{float(chain['chain_score']):.6f}"
            writer.writerow(row)

    document = build_bridge_document(nodes, links, intralayer_edges, chains)
    (OUTPUT_DIR / "three_layer_bridge_summary.md").write_text(document, encoding="utf-8")
    (OUTPUT_DIR / "政策需求供给能力传导链说明.md").write_text(document, encoding="utf-8")


def draw_figure(nodes, links, positions, intralayer_edges) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12.8, 7.2), facecolor="white")
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.92])
    ax.set_xlim(0, 1.03)
    ax.set_ylim(0.10, 0.90)
    ax.axis("off")

    draw_layer_frames(ax)
    draw_chain_role_labels(ax)
    draw_intralayer_edges(ax, intralayer_edges, positions)
    draw_links(ax, links, positions)
    draw_nodes(ax, nodes, positions, links, intralayer_edges)

    for suffix in ["png", "pdf", "svg", "tiff"]:
        dpi = 600 if suffix in {"png", "tiff"} else None
        fig.savefig(
            OUTPUT_STEM.with_suffix(f".{suffix}"),
            dpi=dpi,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


def main() -> None:
    nodes = load_nodes()
    intralayer_edges = load_intralayer_edges(nodes)
    links = select_links(nodes, intralayer_edges)
    positions = assign_positions(nodes)
    draw_figure(nodes, links, positions, intralayer_edges)
    write_outputs(nodes, links, positions, intralayer_edges)
    print("政策-需求-供给三层能力关联图")
    print(f"政策端节点数: {len(nodes['policy'])}")
    print(f"需求端节点数: {len(nodes['demand'])}")
    print(f"供给端节点数: {len(nodes['supply'])}")
    print(f"跨层虚线数: {len(links)}")
    print(f"已保存: {OUTPUT_STEM}.png / .pdf / .svg / .tiff")


if __name__ == "__main__":
    main()
