#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from open_code_competencies_wide import (
    build_inventory,
    clean_text,
    has,
    read_demand_rows,
    read_supply_rows,
    short_sample,
    source_balance,
    write_csv,
)


OUTPUT_DIR = Path("供需能力开放编码_中观边界强化口径_全量")


def broad_code(a):
    """Broader analysis codebook: around 30-40 meso modules, no external API."""
    # 船舶产业链
    if has(a, "船|船舶|船体|舾装|船厂|造船|修船|船级社|游艇|游轮|潜艇|公务船|巡逻船|船员|水手|轮机|机舱|柴油机|船舶与海洋工程"):
        if has(a, "挖泥船|疏浚船"):
            return "港口航道水运工程能力", "挖泥船与疏浚施工归入港口航道水运工程", "confirmed"
        if has(a, "英语|沟通|国际|交流|团队"):
            return "团队沟通国际化能力", "船舶相关沟通、英语和团队协作上收到通用沟通模块", "confirmed"
        if has(a, "伦理|社会责任|行业认知|可持续|人文素养"):
            return "工程伦理安全可持续能力", "船舶相关伦理责任上收到通用伦理模块", "confirmed"
        if has(a, "创新|创业|实践|实习|实验|测试|科研|课题|人才培养"):
            return "科研实验创新实践能力", "船舶相关科研实验实践上收到创新实践模块", "confirmed"
        if has(a, "船舶与海洋工程") and has(a, "英语|沟通|国际|交流"):
            return "团队沟通国际化能力", "船舶海洋工程中的沟通国际化能力上收到通用模块", "confirmed"
        if has(a, "船舶与海洋工程") and has(a, "伦理|社会责任|行业认知|可持续"):
            return "工程伦理安全可持续能力", "船舶海洋工程中的伦理责任上收到通用模块", "confirmed"
        if has(a, "船舶与海洋工程") and has(a, "创新|创业|实践|实习|实验|测试|科研|课题|研究"):
            return "科研实验创新实践能力", "船舶海洋工程中的科研实验实践上收到创新实践模块", "confirmed"
        if has(a, "船舶与海洋工程") and has(a, "基础|理论|知识|力学|流体|问题分析|综合|专业|工具|模拟|图纸|技术服务"):
            return "船舶设计研发能力", "船舶海洋工程基础、分析与工具使用并入船舶设计研发", "confirmed"
        if has(a, "船舶代理|船代|船舶货运|货运|积载|配载|舱单|进出港|出入境|进出境|在港|港口作业|码头|泊位|靠泊|靠离泊|调度|装卸|联检|申报|单证|租船|干散货|海上物流"):
            return "港航物流与航运业务能力", "船舶代理、货运、配载和进出港业务归入港航物流", "confirmed"
        if has(a, "电气|电力|自动化|电子电气|电机|电源|变频|电控|报警|控制器|低压配电|电站|三电|机电成本"):
            return "船舶电气自动化能力", "对象为船舶电气自动化系统", "confirmed"
        if has(a, "轮机|机舱|柴油机|主机|辅机|动力|燃油|轴系|通风空调|制冷|推进|机械运用|辅助机械"):
            return "船舶轮机动力能力", "对象为船舶轮机与动力系统", "confirmed"
        if has(a, "通信|通讯|导航|定位|雷达|电子海图|GMDSS|网络安全|信息系统|数据中心|SCADA|软件|嵌入式|协议|仿真|智能|无人船|绿色船舶|新能源|清洁能源|监控系统|工业互联网|工控系统|信号识别|信号采集"):
            return "船舶通导与智能系统能力", "对象为船舶通导、信息化与智能绿色系统", "confirmed"
        if has(a, "运营|海务|机务|安全|应急|防污染|环保|消防|事故|HSE|法规|合规|驾驶|操纵|操作|航行|航海技术|靠离泊|值班|避碰|甲板|水手|船舶管理|船员|船员管理|船员服务|船长|证书|签证|培训|派遣|调配|登轮|审验|检查|查验|公估|勘验|损失评估|污染防治"):
            return "船舶运营安全管理能力", "对象为船舶运营、安全与船员服务", "confirmed"
        if has(a, "船务|贸易|买卖|经纪|市场|商务|客户|合同|采购|供应链|供应商|售后|技术支持|经营|报价|租赁|融资|资产|财务|费用|物资|销售|行销|投标"):
            return "船舶市场商务与供应链能力", "对象为船舶产品、市场、采购和供应链", "confirmed"
        if has(a, "建造|制造|生产|工艺|施工|安装|分段|涂装|焊接|加工|装配|质量|可靠性|检验|检测|探伤|调试|交付|监造|修造|修船|修理|坞修|维修|维护|维保|保养|故障诊断|项目|现场|设备设施|技术问题|全生命周期|总包|下料|库存|起重|腐蚀|防护"):
            return "船舶建造制造与质量能力", "对象为船舶建造、修造、质量与设备维护", "confirmed"
        if has(a, "设计|研发|结构|总体|性能|稳性|水动力|船型|外观|内装|三维|建模|制图|放样|规范|计算|机电工程|机电技术|船机电|设备管理|装备专业|拼板|图纸|技术中心|技术管理|阀门|选型|技术方案|声学|超材料"):
            return "船舶设计研发能力", "对象为船舶设计、研发与工程分析", "confirmed"
        return "船舶综合工程能力", "船舶对象明确但模块边界不清", "tentative"

    # 海洋工程、海上能源与港航
    if has(a, "海上风电|海上风机|漂浮式风电|漂浮式风机|漂浮式能源岛|风资源|升压站|风电工程|海洋能|潮流能|波浪能|漂浮式光伏|海上能源|海上光伏|可再生能源|深远海绿色能源|光伏电站|LNG|接收站|油气|甲醇|储能|新能源|柔直输电"):
        return "海洋能源与海上风电工程能力", "海上风电、海洋能源和涉海能源合并", "confirmed"
    if has(a, "海工|海洋工程|海洋平台|海洋装备|海洋机电液|FPSO|海底管道|疏浚管线|上部模块|水下|浮体|动态缆|柔性管缆|海洋管缆|海管|脐带缆|海上工程|海上施工|海上作业|海上吊装|海上浮式结构|海上大型钢结构|海上项目|海油装备"):
        if has(a, "项目|管理|分包|界面|变更|成本|进度|计划|现场|施工|安装|建造|生产|质量|运维|市场|商务"):
            return "海洋工程项目建设管理能力", "海洋工程建设、项目和运维管理合并", "confirmed"
        return "海洋工程装备设计制造能力", "海洋工程装备、结构和系统设计制造合并", "confirmed"
    if has(a, "海缆|海洋软管"):
        if has(a, "生产|安装|管理|交付|合同"):
            return "海洋工程项目建设管理能力", "海缆生产安装和交付归入海洋工程项目建设管理", "confirmed"
        return "海洋工程装备设计制造能力", "海缆和海洋软管研发设计归入海洋工程装备", "confirmed"
    if has(a, "港口|港航|航道|水运|码头|海岸|近海工程|岸电|门机|起重|堆场"):
        if has(a, "机电|机械|电气|设备|岸电|门机|起重|供配电|维修|运维|智慧|智能|信息化|物联网|平台|算法|无人港口"):
            return "港口机电与智慧港口能力", "港口机电设备和智慧港口技术合并", "confirmed"
        return "港口航道水运工程能力", "港口航道、水运与近海工程合并", "confirmed"
    if has(a, "港机"):
        return "港口机电与智慧港口能力", "港机操作维护归入港口机电与智慧港口", "confirmed"
    if has(a, "航运|海运|远洋|租船|货代|多式联运|运输代理|航线|船东|船代|外贸单证|班轮|干散货|油轮|港口物流|港口作业|仓储|订舱|配载|堆场|供应链|物流|海上运输"):
        if has(a, "法律|法规|政策|保险|合同|海商法|贸易"):
            return "海事法律监管能力", "航运法务、保险和贸易规则合并", "confirmed"
        return "港航物流与航运业务能力", "港航物流、海运业务和运输组织合并", "confirmed"
    if has(a, "海事|海域使用|危防|海商法"):
        return "海事法律监管能力", "海事管理和航运法务监管合并", "confirmed"
    if has(a, "航海|GMDSS|无线电导航|北斗|卫星导航"):
        return "航海驾驶与通导操作能力", "航海技术、通导操作和航海仪器合并", "confirmed"

    # 海洋科学与水产
    if has(a, "水声|声学|声呐|声纳|声场|水听器|声信息|海洋通信|海洋光通信"):
        return "水声声学与海洋通信技术能力", "水声、声学与涉海通信合并", "confirmed"
    if has(a, "海洋信息|数字海洋|智慧海洋|海洋数据|海洋软件|海洋人工智能|海洋智能|海洋GIS|海洋大数据|海洋电子|海洋测控|海洋无人|海洋时空数据|海洋仪表|海洋前沿技术|海洋技术|海洋.*Web|海洋.*硬件"):
        return "海洋信息智能数据能力", "海洋信息、数据、智能和仪器技术合并", "confirmed"
    if has(a, "海洋调查|海洋观测|海洋测量|海洋测绘|海洋仪器|海洋传感|海洋现场调查|海洋现场观测|海洋监测仪器|探测|遥感|卫星海洋|采样|样品采集|物探|测深|GIS|3S技术|地理信息|地理学"):
        return "海洋调查观测测绘能力", "海洋调查、观测、采样和测绘合并", "confirmed"
    if has(a, "海洋环境|海洋环保|环境监测|生态环境|环境评价|海洋环评|污染|水质|生态调查|生态保护|水环境|智慧环境|海域使用论证|海洋分析检测|海上环境"):
        return "海洋环境监测评价治理能力", "海洋环境监测、评价与治理合并", "confirmed"
    if has(a, "物理海洋|海洋动力|海洋数值|海洋气象|气象海洋|大气海洋|数值模拟|HPC|大气|气象|天气|气候"):
        return "物理海洋气象分析能力", "物理海洋、气象和数值分析合并", "confirmed"
    if has(a, "海洋地质|地球物理|海底|矿产|地貌|古海洋|海洋古环境|地球科学|地质|地震|地层|岩矿|沉积盆地"):
        return "海洋地质地球物理能力", "海洋地质、地球物理和地球科学合并", "confirmed"
    if has(a, "海洋生物|浮游|底栖|微藻|藻类|生物海洋|海洋生态|海洋馆|海洋动物|保育|海洋生命科学"):
        return "海洋生物生态保育能力", "海洋生物、生态和保育合并", "confirmed"
    if has(a, "水产|养殖|渔业|对虾|鱼类|贝类|苗种|病害|饲料|营养|动保|水生|增殖|捕捞|牧场|网箱|分子育种|工厂化循环水"):
        if has(a, "加工|食品|质量|检测|采购|市场|销售"):
            return "水产品加工质量与市场服务能力", "水产品加工、质量和市场服务合并", "confirmed"
        return "水产养殖渔业技术能力", "水产养殖、病害、育种和渔业技术合并", "confirmed"
    if has(a, "海洋材料|海洋.*高分子|绳网材料|海洋化学|化学海洋|海水分析|地球化学|海洋药物"):
        return "海洋材料化学与生物医药能力", "海洋材料、化学和生物医药合并", "confirmed"
    if has(a, "海洋科学|海洋交叉|海洋专业|海洋资源|海洋基础|海洋研究|海洋实验|海洋实践|海洋实习|海洋学科竞赛|海洋科技"):
        return "海洋科学综合研究能力", "海洋科学综合研究和实践合并", "confirmed"

    # 邻近工程与通用支撑
    if has(a, "电子|电路|电气|PLC|自动化|控制系统|智能控制|液压|气动|通信|信号|微波|FPGA|单片机|传感器|信息系统|光电|光纤|数据中心|测控|智能仪表|微控制器|机器视觉|工业控制|仪器操作与监测"):
        return "电子通信与自动控制能力", "电子信息、通信、测控和自动化合并", "confirmed"
    if has(a, "人工智能|机器学习|深度学习|大数据|数据分析|数据处理|数据采集|数据库|算法|软件|嵌入式|编程|C/C\\+\\+|Linux|前端|ERP|信息处理|信息技术|数字化|智能系统|计算机网络|信息安全|优化方法|计算方法|仿真|三维建模|专业软件|现代.*工具|工程工具"):
        return "数字化工具与软件应用能力", "通用信息技术、软件和数字工具合并", "confirmed"
    if has(a, "机械|机电|机器人|智能制造|智能装备|材料|焊接材料|成型|腐蚀|防腐|能源动力|能源与动力|内燃机|热能|制冷|低温|空调|动力机械|动力定位|工业能源|变压器|压力容器|传动与控制|化学电源|工艺技术改进"):
        return "机械材料能源动力能力", "机械、材料、能源动力和装备支撑合并", "confirmed"
    if has(a, "交通|运输工程|道路|桥梁|土木|岩土|地下工程|水利水电|水文|水资源|水工|农业水利"):
        return "土木交通水利工程能力", "土木交通、水利水文和基础设施合并", "confirmed"
    if has(a, "环境工程|环境规划|环境管理|环境保护|环境影响|环境治理|环境修复|环境生态修复|环境毒理|环境统计|固体废物|废弃物|废水|废气|污染治理|环保工程|生态修复|生态规划|土壤|地下水"):
        return "环境工程治理能力", "环境工程和污染治理支撑合并", "confirmed"
    if has(a, "食品|农产品加工|生物化学|分子生物|分子生态|细胞|基因|微生物|蛋白|化学分析|化学实验|化学学科|药学|生命科学|生物信息|生物统计|生物多样性|生物学|生物工程|生物技术|生态学"):
        return "生物化学食品支撑能力", "生物、化学和食品基础支撑合并", "confirmed"

    # 可迁移能力，但保持论文可解释性
    if has(a, "工程管理|项目管理|经济决策|工程经济|工程结算|决算|成本|造价|费用|招标|投标|报价|市场|客户|销售|商务|企业竞争|人力资源|经营管理|产业规划|质量.*管控|质量.*改进|无损检测|体系认证|合规管理|标准化|研制流程合规|技术文件审核"):
        return "工程管理经济质量能力", "工程管理、经济、市场和质量合规合并", "confirmed"
    if has(a, "工程伦理|工程与社会|职业规范|职业道德|社会责任|可持续|安全|应急|风险|消防|救助|救捞|打捞|劳动精神|工匠精神|法规|法律|政策|执法"):
        return "工程伦理安全可持续能力", "伦理、安全、法律政策和可持续合并", "confirmed"
    if has(a, "团队|沟通|协作|合作|组织协调|领导力|跨文化|国际视野|国际沟通|国际化|外语|英语|英文|双语"):
        return "团队沟通国际化能力", "团队沟通、外语和国际化合并", "confirmed"
    if has(a, "文献|科技写作|论文|报告撰写|学术写作|学术表达|教材|教师|双师型|教学"):
        return "文献写作与教育教学能力", "学术表达、文献写作和教学合并", "confirmed"
    if has(a, "科学研究|科研|实验|测试|创新|创业|实践|实习|毕业设计|批判性思维|自主学习|终身学习|持续学习|多学科"):
        return "科研实验创新实践能力", "科研、实验、创新实践和学习发展合并", "confirmed"
    if has(a, "工程知识|工程问题|复杂工程|问题分析|发现分析与解决问题|设计开发解决方案|建模|工程设计|工程制图|数理|数学|物理|力学|流体|水动力|泥沙|结构|振动|噪声|抗震|防灾|概率论|随机过程|实变函数|泛函|基础理论|自然科学|计算"):
        return "工程基础与问题分析能力", "工程基础、数理和问题分析合并", "confirmed"

    return "低频跨域专业综合能力", "低频长尾按跨域专业综合归并", "tentative"


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    supply_rows = read_supply_rows()
    demand_rows = read_demand_rows()
    inventory = build_inventory(supply_rows, demand_rows)

    inventory_fields = [
        "ability_id", "original_ability", "side",
        "supply_occurrences", "supply_file_count",
        "demand_occurrences", "demand_record_count",
        "supply_evidence_sample", "demand_evidence_sample", "demand_job_sample",
    ]
    write_csv(OUTPUT_DIR / "ability_inventory_for_audit.csv", inventory, inventory_fields)

    mapping = []
    for row in inventory:
        canonical, rationale, status = broad_code(row["original_ability"])
        mapping.append({
            **row,
            "canonical_competency": canonical,
            "coding_status": status,
            "merge_rationale": rationale,
        })

    mapping_fields = [
        "ability_id", "original_ability", "canonical_competency", "coding_status", "merge_rationale", "side",
        "supply_occurrences", "supply_file_count", "demand_occurrences", "demand_record_count",
        "supply_evidence_sample", "demand_evidence_sample", "demand_job_sample",
    ]
    write_csv(OUTPUT_DIR / "ability_open_coding_mapping.csv", mapping, mapping_fields)

    groups = defaultdict(list)
    for row in mapping:
        groups[row["canonical_competency"]].append(row)

    dictionary = []
    for canonical, rows in groups.items():
        supply = sum(int(r["supply_occurrences"]) for r in rows)
        demand = sum(int(r["demand_occurrences"]) for r in rows)
        statuses = {r["coding_status"] for r in rows}
        dict_status = "含暂定项" if "tentative" in statuses else "confirmed"
        dictionary.append({
            "canonical_competency": canonical,
            "original_ability_count": len(rows),
            "supply_occurrences": supply,
            "demand_occurrences": demand,
            "source_balance": source_balance(supply, demand),
            "dictionary_status": dict_status,
            "original_ability_examples": " | ".join(r["original_ability"] for r in rows[:15]),
        })
    dictionary.sort(key=lambda x: (-(x["supply_occurrences"] + x["demand_occurrences"]), x["canonical_competency"]))
    dictionary_fields = [
        "canonical_competency", "original_ability_count", "supply_occurrences", "demand_occurrences",
        "source_balance", "dictionary_status", "original_ability_examples",
    ]
    write_csv(OUTPUT_DIR / "canonical_competency_dictionary.csv", dictionary, dictionary_fields)

    map_by_ability = {row["original_ability"]: row for row in mapping}

    def expand(rows):
        expanded = []
        for row in rows:
            coded = map_by_ability[row["ability"]]
            expanded.append({
                **row,
                "canonical_competency": coded["canonical_competency"],
                "coding_status": coded["coding_status"],
                "merge_rationale": coded["merge_rationale"],
            })
        return expanded

    item_fields = [
        "side", "source_file", "source_index", "job_title", "occupation_name",
        "ability", "canonical_competency", "coding_status", "merge_rationale", "evidence",
    ]
    write_csv(OUTPUT_DIR / "supply_competency_items_coded.csv", expand(supply_rows), item_fields)
    write_csv(OUTPUT_DIR / "demand_competency_items_coded.csv", expand(demand_rows), item_fields)

    status_counts = defaultdict(int)
    for row in mapping:
        status_counts[row["coding_status"]] += 1

    notes = f"""# 供需能力开放编码审计说明（中观边界强化口径，全量）

本轮按 `marine-competency-open-coding` skill 执行：不调用外部 API，不预设外部类别体系。相比上一版 405 个规范技能，本版将低频长尾上收到论文主分析可用的中观能力模块。

## 规模

- 原始唯一 ability：{len(inventory)}
- 供给端明细：{len(supply_rows)}
- 需求端明细：{len(demand_rows)}
- 归纳规范技能：{len(dictionary)}

## 编码状态

- confirmed：{status_counts['confirmed']}
- tentative：{status_counts['tentative']}

## 口径

- 保留船舶、海工、海上风电、港航物流、海洋科学、水产渔业、邻近工程支撑等边界。
- 把低频动作词，如设计、研发、施工、运维、质量、商务、管理，上收到同一专业对象下的能力模块。
- 不再把单次出现的窄任务保留为独立规范技能。
"""
    (OUTPUT_DIR / "open_coding_audit_notes.md").write_text(notes, encoding="utf-8")

    print(f"inventory={len(inventory)}")
    print(f"canonical_competencies={len(dictionary)}")
    print(f"supply_rows={len(supply_rows)}")
    print(f"demand_rows={len(demand_rows)}")
    print("mapping_status=" + json.dumps(dict(status_counts), ensure_ascii=False))
    print(f"output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
