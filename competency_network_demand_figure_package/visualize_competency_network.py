#!/usr/bin/env python3
"""需求端规范能力共现骨干网络图。

该图用于论文正文：保留全部40个规范能力节点，仅绘制可解释的强共现关系，
避免弱边和长标签把网络结构淹没。
"""

import csv
import math
import textwrap
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np


for name in [
    "Hiragino Sans GB",
    "PingFang SC",
    "PingFang HK",
    "Heiti TC",
    "STHeiti",
    "Songti SC",
]:
    try:
        fm.findfont(name, fallback_to_default=False)
        matplotlib.rcParams["font.family"] = [name, "sans-serif"]
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
        "axes.linewidth": 0.7,
    }
)

INPUT_DIR = Path("供需能力开放编码_中观边界强化口径_全量")
DEMAND_FILE = INPUT_DIR / "demand_competency_items_coded.csv"
DICT_FILE = INPUT_DIR / "canonical_competency_dictionary.csv"
OUTPUT_STEM = Path("competency_network_demand")


CATEGORIES = {
    "船舶工程": [
        "船舶建造制造与质量能力",
        "船舶设计研发能力",
        "船舶电气自动化能力",
        "船舶轮机动力能力",
        "船舶运营安全管理能力",
        "船舶通导与智能系统能力",
        "船舶市场商务与供应链能力",
        "船舶综合工程能力",
    ],
    "海洋工程与能源": [
        "海洋工程装备设计制造能力",
        "海洋工程项目建设管理能力",
        "海洋能源与海上风电工程能力",
    ],
    "港航物流与港口": [
        "港航物流与航运业务能力",
        "港口航道水运工程能力",
        "港口机电与智慧港口能力",
    ],
    "信息技术与数字化": [
        "数字化工具与软件应用能力",
        "电子通信与自动控制能力",
        "海洋信息智能数据能力",
        "水声声学与海洋通信技术能力",
    ],
    "海洋科学": [
        "海洋科学综合研究能力",
        "海洋调查观测测绘能力",
        "海洋生物生态保育能力",
        "海洋环境监测评价治理能力",
        "物理海洋气象分析能力",
        "海洋地质地球物理能力",
        "海洋材料化学与生物医药能力",
    ],
    "水产渔业与食品": [
        "水产养殖渔业技术能力",
        "水产品加工质量与市场服务能力",
        "生物化学食品支撑能力",
    ],
    "通用工程基础": [
        "工程基础与问题分析能力",
        "工程管理经济质量能力",
        "机械材料能源动力能力",
        "工程伦理安全可持续能力",
    ],
    "通用素养与交叉": [
        "团队沟通国际化能力",
        "科研实验创新实践能力",
        "文献写作与教育教学能力",
        "航海驾驶与通导操作能力",
        "海事法律监管能力",
        "环境工程治理能力",
        "土木交通水利工程能力",
        "低频跨域专业综合能力",
    ],
}

CAT_COLORS = {
    "船舶工程": "#D95F4A",
    "海洋工程与能源": "#4E79A7",
    "港航物流与港口": "#59A14F",
    "信息技术与数字化": "#8E6BBE",
    "海洋科学": "#2F9C95",
    "水产渔业与食品": "#E28A3B",
    "通用工程基础": "#7C8790",
    "通用素养与交叉": "#B8C0C7",
}

CAT_CENTERS = {
    "船舶工程": (-0.72, 0.04),
    "海洋工程与能源": (-0.10, 0.30),
    "港航物流与港口": (0.45, 0.03),
    "信息技术与数字化": (0.13, 0.70),
    "海洋科学": (0.80, 0.47),
    "水产渔业与食品": (0.56, -0.58),
    "通用工程基础": (-0.25, -0.62),
    "通用素养与交叉": (-0.80, -0.50),
}

CAT_LABEL_POS = {
    "船舶工程": (-0.72, 0.43),
    "海洋工程与能源": (-0.31, 0.53),
    "港航物流与港口": (0.45, 0.34),
    "信息技术与数字化": (0.13, 1.02),
    "海洋科学": (0.80, 0.82),
    "水产渔业与食品": (0.56, -0.18),
    "通用工程基础": (-0.25, -0.24),
    "通用素养与交叉": (-0.84, -0.42),
}


def read_inputs():
    all_skills = []
    with DICT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row["canonical_competency"].strip()
            if name:
                all_skills.append(name)

    job_competencies = defaultdict(set)
    competency_freq = Counter()
    with DEMAND_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            idx = row["source_index"].strip()
            comp = (row.get("canonical_competency") or "").strip()
            if idx and comp:
                job_competencies[idx].add(comp)
                competency_freq[comp] += 1

    for skill in all_skills:
        competency_freq.setdefault(skill, 0)

    return all_skills, job_competencies, competency_freq


def compute_edges(all_skills, job_competencies):
    skill_job_sets = {skill: set() for skill in all_skills}
    for idx, comps in job_competencies.items():
        for comp in comps:
            skill_job_sets.setdefault(comp, set()).add(idx)

    cooccur = Counter()
    for comps in job_competencies.values():
        for a, b in combinations(sorted(comps), 2):
            cooccur[(a, b)] += 1

    edges = []
    for (a, b), count in cooccur.items():
        union = len(skill_job_sets[a] | skill_job_sets[b])
        jaccard = count / union if union else 0
        edges.append((a, b, count, jaccard))

    edges.sort(key=lambda x: (-x[2], -x[3], x[0], x[1]))
    return edges


def select_backbone_edges(edges, all_skills, competency_freq):
    """选择正文图可读的骨干边：强边为主，并保留高频节点的最强关系。"""
    selected = {
        (a, b): (a, b, count, jaccard)
        for a, b, count, jaccard in edges
        if count >= 4 or jaccard >= 0.04
    }

    # 高频节点若未进入骨干网络，补充其最强共现边，避免孤立误读。
    active = {skill for skill in all_skills if competency_freq[skill] >= 20}
    for skill in active:
        if any(skill in key for key in selected):
            continue
        candidates = [edge for edge in edges if skill in edge[:2]]
        if candidates and candidates[0][2] >= 2:
            a, b, count, jaccard = candidates[0]
            selected[(a, b)] = (a, b, count, jaccard)

    return sorted(selected.values(), key=lambda x: (-x[2], -x[3], x[0], x[1]))


def build_layout(all_skills, edges, competency_freq, skill_cat):
    graph = nx.Graph()
    graph.add_nodes_from(all_skills)
    graph.add_weighted_edges_from([(a, b, count) for a, b, count, _ in edges])

    pos = {}
    max_freq = max(competency_freq.values()) or 1

    for cat, skills in CATEGORIES.items():
        cx, cy = CAT_CENTERS[cat]
        present = [skill for skill in skills if skill in all_skills]
        if not present:
            continue
        present.sort(key=lambda s: (-competency_freq[s], s))

        radius = 0.15 + 0.018 * len(present)
        if cat == "船舶工程":
            radius = 0.23
        elif cat in {"海洋科学", "通用素养与交叉"}:
            radius = 0.21

        for i, skill in enumerate(present):
            if len(present) == 1:
                pos[skill] = np.array([cx, cy])
                continue
            angle = (2 * math.pi * i / len(present)) + 0.38
            freq_pull = 1 - 0.30 * math.sqrt(competency_freq[skill] / max_freq)
            x = cx + radius * freq_pull * math.cos(angle)
            y = cy + radius * 0.78 * freq_pull * math.sin(angle)
            pos[skill] = np.array([x, y])

    fixed = list(pos)
    spring_pos = nx.spring_layout(
        graph,
        pos=pos,
        fixed=fixed,
        seed=24,
        iterations=120,
        weight="weight",
        k=0.36,
    )

    # 轻微拉回类别锚点，保证类别结构稳定。
    blended = {}
    for skill in all_skills:
        cat = skill_cat.get(skill, "")
        base = pos.get(skill, np.array([0.0, 0.0]))
        sprung = spring_pos.get(skill, base)
        blended[skill] = 0.82 * base + 0.18 * sprung
        if cat in CAT_CENTERS:
            center = np.array(CAT_CENTERS[cat])
            blended[skill] = center + 1.02 * (blended[skill] - center)

    return blended


def wrap_cn(text, width=8):
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=True))


def skill_codes(all_skills):
    code_prefix = {
        "船舶工程": "A",
        "海洋工程与能源": "B",
        "港航物流与港口": "C",
        "信息技术与数字化": "D",
        "海洋科学": "E",
        "水产渔业与食品": "F",
        "通用工程基础": "G",
        "通用素养与交叉": "H",
    }
    codes = {}
    for cat, skills in CATEGORIES.items():
        prefix = code_prefix[cat]
        present = [skill for skill in skills if skill in all_skills]
        for idx, skill in enumerate(present, start=1):
            codes[skill] = f"{prefix}{idx}"
    return codes


def draw_cluster_backgrounds(ax):
    for cat, center in CAT_CENTERS.items():
        color = CAT_COLORS[cat]
        radius = 0.28
        if cat == "船舶工程":
            radius = 0.34
        elif cat in {"海洋科学", "通用素养与交叉"}:
            radius = 0.31
        elif cat in {"海洋工程与能源", "港航物流与港口", "水产渔业与食品"}:
            radius = 0.24

        ax.add_patch(
            Circle(
                center,
                radius=radius,
                facecolor=color,
                edgecolor=color,
                alpha=0.055,
                linewidth=1.0,
                zorder=0,
            )
        )
        lx, ly = CAT_LABEL_POS.get(cat, (center[0], center[1] + radius + 0.04))
        ax.text(
            lx,
            ly,
            cat,
            ha="center",
            va="bottom",
            fontsize=7.2,
            color=color,
            fontweight="bold",
            zorder=5,
        )


def draw_edges(ax, edges, pos):
    max_weight = max((edge[2] for edge in edges), default=1)
    for i, (a, b, count, _jaccard) in enumerate(edges):
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        width = 0.35 + 2.25 * math.sqrt(count / max_weight)
        alpha = 0.18 + 0.38 * math.sqrt(count / max_weight)
        curve = 0.10 if i % 2 == 0 else -0.10
        if count >= 10:
            curve *= 0.55
        edge = FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-",
            mutation_scale=1,
            linewidth=width,
            color="#52606D",
            alpha=alpha,
            connectionstyle=f"arc3,rad={curve}",
            capstyle="round",
            joinstyle="round",
            zorder=1,
        )
        ax.add_patch(edge)


def draw_nodes(ax, all_skills, pos, competency_freq, skill_cat, codes):
    freqs = np.array([competency_freq[skill] for skill in all_skills], dtype=float)
    max_freq = freqs.max() if len(freqs) else 1
    min_active = freqs[freqs > 0].min() if np.any(freqs > 0) else 0

    for skill in all_skills:
        freq = competency_freq[skill]
        cat = skill_cat.get(skill, "")
        x, y = pos[skill]
        if freq > 0:
            scaled = (math.sqrt(freq) - math.sqrt(min_active)) / (
                math.sqrt(max_freq) - math.sqrt(min_active) + 1e-9
            )
            size = 90 + 720 * scaled
            alpha = 0.96
            edge_color = "#263238"
            line_width = 0.65
        else:
            size = 52
            alpha = 0.32
            edge_color = "#B7BFC7"
            line_width = 0.4

        ax.scatter(
            x,
            y,
            s=size,
            c=CAT_COLORS.get(cat, "#A0A6AD"),
            edgecolors=edge_color,
            linewidth=line_width,
            alpha=alpha,
            zorder=3,
        )

        code = codes.get(skill, "")
        if code:
            ax.text(
                x,
                y,
                code,
                ha="center",
                va="center",
                fontsize=5.8 if freq < 100 else 6.3,
                fontweight="bold",
                color="white",
                zorder=4,
                path_effects=[pe.withStroke(linewidth=1.0, foreground="#263238", alpha=0.65)],
            )


def draw_key_node_labels(ax, all_skills, pos, competency_freq, skill_cat):
    key_skills = [skill for skill in all_skills if competency_freq[skill] >= 100]
    for skill in key_skills:
        freq = competency_freq[skill]
        x, y = pos[skill]
        cat = skill_cat.get(skill, "")
        cx, cy = CAT_CENTERS.get(cat, (0, 0))
        vec = np.array([x - cx, y - cy])
        norm = np.linalg.norm(vec) or 1
        vec = vec / norm
        label_x = x + 0.044 * vec[0]
        label_y = y + 0.048 * vec[1]
        ha = "left" if vec[0] >= 0 else "right"
        va = "bottom" if vec[1] >= -0.1 else "top"
        ax.text(
            label_x,
            label_y,
            f"{wrap_cn(skill, 7)}\n{freq}",
            ha=ha,
            va=va,
            fontsize=5.6,
            color="#263238",
            linespacing=1.08,
            bbox=dict(
                boxstyle="round,pad=0.13,rounding_size=0.04",
                facecolor="white",
                edgecolor="none",
                alpha=0.78,
            ),
            zorder=5,
        )


def draw_index_panel(ax, all_skills, competency_freq, codes, total_jobs):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.0,
        0.985,
        "节点索引",
        fontsize=8.8,
        fontweight="bold",
        color="#18242F",
        va="top",
    )
    ax.text(
        0.0,
        0.952,
        "编号对应完整规范能力；括号内为需求岗位提及频次/占比",
        fontsize=5.8,
        color="#52606D",
        va="top",
    )

    columns = [
        ["船舶工程", "海洋工程与能源", "港航物流与港口", "信息技术与数字化"],
        ["海洋科学", "水产渔业与食品", "通用工程基础", "通用素养与交叉"],
    ]
    x_positions = [0.0, 0.505]
    col_width = 0.475

    for col_idx, cats in enumerate(columns):
        x0 = x_positions[col_idx]
        y = 0.900
        for cat in cats:
            color = CAT_COLORS[cat]
            ax.text(
                x0,
                y,
                cat,
                fontsize=6.6,
                fontweight="bold",
                color=color,
                va="top",
            )
            y -= 0.024
            for skill in CATEGORIES[cat]:
                if skill not in all_skills:
                    continue
                freq = competency_freq[skill]
                pct = freq / total_jobs * 100 if total_jobs else 0
                code = codes[skill]
                ax.text(
                    x0,
                    y,
                    code,
                    fontsize=5.6,
                    fontweight="bold",
                    color=color,
                    va="top",
                )
                ax.text(
                    x0 + 0.047,
                    y,
                    f"{wrap_cn(skill, 10)} ({freq}, {pct:.1f}%)",
                    fontsize=5.25,
                    color="#263238" if freq else "#9AA3AB",
                    va="top",
                    linespacing=1.02,
                )
                y -= 0.036 if len(skill) > 12 else 0.027
            y -= 0.012

    ax.plot([0.49, 0.49], [0.065, 0.905], color="#E1E5E8", lw=0.6)
    ax.text(
        0.0,
        0.035,
        "注：网络图展示强共现骨干边；完整原始共现关系保留在数据计算中。",
        fontsize=5.5,
        color="#6B747C",
        va="bottom",
    )


def draw_size_legend(ax):
    x0, y0 = -1.10, -1.00
    entries = [(100, "低"), (320, "中"), (700, "高")]
    ax.text(x0, y0 + 0.13, "岗位提及频次", fontsize=6.2, color="#52606D", ha="left")
    for i, (size, label) in enumerate(entries):
        ax.scatter(
            x0 + 0.09 * i,
            y0 + 0.04,
            s=size,
            facecolor="#D9DEE3",
            edgecolor="#263238",
            linewidth=0.5,
            zorder=6,
        )
        ax.text(x0 + 0.09 * i, y0 - 0.055, label, ha="center", va="top", fontsize=5.8)


def draw_nodes_and_labels(ax, all_skills, pos, competency_freq, skill_cat, total_jobs):
    """保留旧接口，便于外部复用；正文图改用编号节点。"""
    for skill in all_skills:
        freq = competency_freq[skill]
        x, y = pos[skill]
        cat = skill_cat.get(skill, "")
        cx, cy = CAT_CENTERS.get(cat, (0, 0))
        vec = np.array([x - cx, y - cy])
        norm = np.linalg.norm(vec) or 1
        vec = vec / norm
        label_x = x + 0.020 * vec[0]
        label_y = y + 0.025 * vec[1]
        ha = "left" if vec[0] >= 0 else "right"
        va = "bottom" if vec[1] >= -0.12 else "top"
        fontsize = 5.9 if freq >= 50 else 5.45
        text_color = "#263238" if freq > 0 else "#9AA3AB"
        pct = freq / total_jobs * 100 if total_jobs else 0
        label = f"{wrap_cn(skill, 8)}\n{freq} / {pct:.1f}%"

        ax.text(
            label_x,
            label_y,
            label,
            ha=ha,
            va=va,
            fontsize=fontsize,
            color=text_color,
            linespacing=1.12,
            bbox=dict(
                boxstyle="round,pad=0.16,rounding_size=0.06",
                facecolor="white",
                edgecolor="none",
                alpha=0.74,
            ),
            zorder=4,
        )


def draw_legends(ax):
    category_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markeredgecolor="#263238",
            markeredgewidth=0.5,
            markerfacecolor=color,
            markersize=6.5,
            label=cat,
        )
        for cat, color in CAT_COLORS.items()
    ]
    leg1 = ax.legend(
        handles=category_handles,
        title="能力类别",
        loc="lower left",
        bbox_to_anchor=(0.012, 0.03),
        ncol=2,
        fontsize=6.2,
        title_fontsize=6.8,
        frameon=True,
        framealpha=0.92,
        borderpad=0.7,
        handletextpad=0.5,
        columnspacing=0.8,
    )
    leg1.get_frame().set_linewidth(0.4)
    leg1.get_frame().set_edgecolor("#D6DBDF")
    ax.add_artist(leg1)

    size_handles = [
        plt.scatter([], [], s=size, facecolor="#D9DEE3", edgecolor="#263238", linewidth=0.5)
        for size in [100, 320, 650]
    ]
    leg2 = ax.legend(
        size_handles,
        ["低", "中", "高"],
        title="岗位提及频次",
        loc="lower right",
        bbox_to_anchor=(0.988, 0.035),
        scatterpoints=1,
        fontsize=6.2,
        title_fontsize=6.8,
        frameon=True,
        framealpha=0.92,
        borderpad=0.7,
        labelspacing=0.9,
    )
    leg2.get_frame().set_linewidth(0.4)
    leg2.get_frame().set_edgecolor("#D6DBDF")


def save_outputs(fig):
    fig.savefig(OUTPUT_STEM.with_suffix(".png"), dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(OUTPUT_STEM.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUTPUT_STEM.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(OUTPUT_STEM.with_suffix(".tiff"), dpi=600, bbox_inches="tight", facecolor="white")


def main():
    all_skills, job_competencies, competency_freq = read_inputs()
    raw_edges = compute_edges(all_skills, job_competencies)
    edges = select_backbone_edges(raw_edges, all_skills, competency_freq)
    codes = skill_codes(all_skills)

    skill_cat = {}
    for cat, skills in CATEGORIES.items():
        for skill in skills:
            skill_cat[skill] = cat

    pos = build_layout(all_skills, edges, competency_freq, skill_cat)
    total_jobs = len(job_competencies)

    fig = plt.figure(figsize=(11.2, 7.0), facecolor="white")
    ax = fig.add_axes([0.035, 0.08, 0.61, 0.83])
    ax_index = fig.add_axes([0.675, 0.08, 0.30, 0.83])
    ax.set_aspect("equal")
    ax.set_facecolor("white")

    draw_cluster_backgrounds(ax)
    draw_edges(ax, edges, pos)
    draw_nodes(ax, all_skills, pos, competency_freq, skill_cat, codes)
    draw_size_legend(ax)
    draw_index_panel(ax_index, all_skills, competency_freq, codes, total_jobs)

    fig.text(
        0.035,
        0.965,
        "需求端规范能力共现骨干网络",
        ha="left",
        va="top",
        fontsize=10.5,
        fontweight="bold",
        color="#18242F",
    )
    fig.text(
        0.035,
        0.932,
        "节点大小表示岗位提及频次；边宽表示岗位内共现次数；正文图显示强共现骨干关系，完整能力名称见右侧索引",
        ha="left",
        va="top",
        fontsize=6.6,
        color="#52606D",
    )
    fig.text(
        0.642,
        0.045,
        f"n = {total_jobs} 个需求岗位；节点 = {len(all_skills)}；骨干边 = {len(edges)} / 原始共现边 = {len(raw_edges)}",
        ha="right",
        va="bottom",
        fontsize=6.1,
        color="#6B747C",
    )

    ax.set_xlim(-1.18, 1.18)
    ax.set_ylim(-1.08, 1.10)
    ax.axis("off")
    save_outputs(fig)

    print(f"岗位数: {total_jobs}")
    print(f"技能节点数: {len(all_skills)}")
    print(f"原始共现边数: {len(raw_edges)}")
    print(f"骨干边数: {len(edges)}")
    print(f"已保存: {OUTPUT_STEM}.png / .pdf / .svg / .tiff")


if __name__ == "__main__":
    main()
