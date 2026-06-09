#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import json
import re
from collections import defaultdict
from pathlib import Path


SUPPLY_CHUNKS = "供给端_DeepSeek能力提取_141份_flash_当前prompt/supply_competency_chunks.jsonl"
DEMAND_ITEMS = "需求端_DeepSeek能力提取_1580条_flash_海洋中观prompt/demand_competency_items.csv"
OUTPUT_DIR = Path("供需能力开放编码_中观偏上_全量")


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def clean_ability(value):
    text = clean_text(value).replace(" ", "")
    text = re.sub(r"[。；;，,、]+$", "", text)
    return text


def ensure_ability(value):
    text = clean_ability(value)
    text = re.sub(r"^(掌握|具备|熟悉|了解|能够|负责|具有)", "", text)
    text = re.sub(r"(意识|素养)$", "能力", text)
    if text and not text.endswith("能力"):
        text += "能力"
    return text


def short_sample(values, max_items=3, max_chars=80):
    seen = []
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        seen.append(text)
        if len(seen) >= max_items:
            break
    return " | ".join(seen)


def has(text, *patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def read_supply_rows():
    rows = []
    with Path(SUPPLY_CHUNKS).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            if not obj.get("ok"):
                continue
            source_file = obj.get("source_file", "")
            for item in (obj.get("parsed") or {}).get("items") or []:
                ability = clean_ability(item.get("ability"))
                if not ability:
                    continue
                rows.append({
                    "side": "supply",
                    "source_file": source_file,
                    "source_index": "",
                    "job_title": "",
                    "occupation_name": "",
                    "ability": ability,
                    "evidence": clean_text(item.get("evidence")),
                })
    return rows


def read_demand_rows():
    rows = []
    with Path(DEMAND_ITEMS).open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ability = clean_ability(row.get("ability"))
            if not ability:
                continue
            rows.append({
                "side": "demand",
                "source_file": "",
                "source_index": clean_text(row.get("source_index")),
                "job_title": clean_text(row.get("招聘岗位")),
                "occupation_name": clean_text(row.get("occupation_name")),
                "ability": ability,
                "evidence": clean_text(row.get("evidence")),
            })
    return rows


def build_inventory(supply_rows, demand_rows):
    stats = {}
    for ability in sorted({row["ability"] for row in supply_rows + demand_rows}):
        stats[ability] = {
            "original_ability": ability,
            "supply_occurrences": 0,
            "supply_files": set(),
            "demand_occurrences": 0,
            "demand_records": set(),
            "supply_evidence": [],
            "demand_evidence": [],
            "demand_jobs": [],
        }
    for row in supply_rows:
        item = stats[row["ability"]]
        item["supply_occurrences"] += 1
        item["supply_files"].add(row["source_file"])
        item["supply_evidence"].append(row["evidence"])
    for row in demand_rows:
        item = stats[row["ability"]]
        item["demand_occurrences"] += 1
        item["demand_records"].add(row["source_index"])
        item["demand_evidence"].append(row["evidence"])
        item["demand_jobs"].append(row["job_title"])

    rows = []
    for idx, item in enumerate(sorted(
        stats.values(),
        key=lambda x: (-(x["supply_occurrences"] + x["demand_occurrences"]), x["original_ability"]),
    ), start=1):
        sides = []
        if item["supply_occurrences"]:
            sides.append("supply")
        if item["demand_occurrences"]:
            sides.append("demand")
        rows.append({
            "ability_id": idx,
            "original_ability": item["original_ability"],
            "side": "+".join(sides),
            "supply_occurrences": item["supply_occurrences"],
            "supply_file_count": len(item["supply_files"]),
            "demand_occurrences": item["demand_occurrences"],
            "demand_record_count": len(item["demand_records"]),
            "supply_evidence_sample": short_sample(item["supply_evidence"]),
            "demand_evidence_sample": short_sample(item["demand_evidence"]),
            "demand_job_sample": short_sample(item["demand_jobs"], max_chars=40),
        })
    return rows


def code_ability(a):
    """Open-coding codebook, medium-high grain. Ordered rules are intentional."""
    # 通用与基础能力
    if has(a, "自主.*终身|终身.*自主|终身学习|自主学习|自主发展"):
        return "自主学习发展能力", "同义合并", "confirmed"
    if has(a, "团队|沟通|协作|合作|组织协调|领导力|领导能力") and not has(a, "项目管理|船员管理|团队管理|客户|市场|商务"):
        return "团队协作组织沟通能力", "同类通用能力合并", "confirmed"
    if has(a, "跨文化|国际视野|国际沟通|国际化视野|国际化交流|全球胜任"):
        return "跨文化沟通国际视野能力", "跨文化与国际视野合并", "confirmed"
    if has(a, "工程伦理|职业规范|职业道德|工程职业|规范履行|规范意识|规范践行|规范遵守|社会责任|工程与社会|可持续发展意识|工程实践社会责任|可信人工智能伦理"):
        return "工程伦理责任能力", "伦理责任类合并", "confirmed"
    if has(a, "环境.*可持续|可持续.*评价|社会.*可持续|资源利用.*环境"):
        return "环境可持续发展评价能力", "可持续评价类合并", "confirmed"
    if has(a, "文献检索|文献查阅|文献阅读|科技写作|论文|报告撰写|学术写作|学术表达"):
        return "文献检索科技写作能力", "科研表达支撑能力", "confirmed"
    if has(a, "数学|数理|物理基础|力学基础|基础理论与方法|自然科学"):
        return "数理基础应用能力", "数理基础类合并", "confirmed"
    if has(a, "企业竞争模拟|人力资源管理|投资项目|招标|投标|成本管控|成本优化|报价建议|经营管理") and not has(a, "船舶|海运|航运|海洋|海上|港口|水产"):
        return "工程管理经济决策能力", "管理经济决策类合并", "confirmed"
    if has(a, "工程管理|项目管理|经济决策|工程经济|项目经济|成本控制|造价|费用控制") and not has(a, "海上风电|港口|航道|船舶|海工|海洋工程|水产|物流|航运"):
        return "工程管理经济决策能力", "通用工程管理经济类合并", "confirmed"
    if has(a, "现代.*工具|工程工具|信息技术应用|计算机.*应用|CAD|BIM|仿真工具|专业软件") and not has(a, "港口|船舶|海洋|航运|海上风电"):
        return "工程信息技术应用能力", "工具与信息技术应用合并", "confirmed"
    if has(a, "人工智能|机器学习|深度学习|大数据|数据分析|数据处理|数据采集|数据库|算法|软件|嵌入式|编程|C/C\\+\\+|Linux|信息处理|数字化|智能系统|智能控制|计算机网络|信息安全|优化方法|计算方法") and not has(a, "海洋|水声|声学|海上风电|港口|航运|船舶|水产|渔业"):
        return "智能信息技术能力", "智能与信息技术类合并", "confirmed"
    if has(a, "工程实践|生产实习|毕业设计|毕业实习|创新创业|创新能力|创业能力|创新实践|创新思维|批判性思维|科学研究|科研|实验设计|实验.*测试|测试技术|实验.*实践|综合实践|工程训练") and not has(a, "船舶|轮机|航海|水产|海洋|港口|气象"):
        return "工程实践创新能力", "实践创新类合并", "confirmed"
    if has(a, "机械设计|机械制造|机械加工|机械电子|机械工程|机械系统|机电系统|传动与控制|机器人|智能制造|智能装备|非标机械|制造质量|工艺技术改进") and not has(a, "船舶|港口|海洋"):
        return "机械设计制造能力", "机械设计制造类合并", "confirmed"
    if has(a, "工程知识|工程问题|复杂工程|问题分析|建模分析|发现分析与解决问题|设计开发解决方案|工程设计|工程制图") and not has(a, "船舶|轮机|航海|水产|海洋|港口|航运|海上风电"):
        return "工程问题分析设计能力", "工程基础分析设计类合并", "confirmed"
    if has(a, "工程测量|测绘|地质勘察|GIS|地理信息|遥感|3S技术") and not has(a, "海洋|港口|航道|水运"):
        return "测绘地理信息能力", "测绘地理信息类合并", "confirmed"
    if has(a, "结构|力学|有限元|振动|噪声") and not has(a, "船舶|轮机|海洋|海工|海上风电|港口|航道"):
        return "工程结构力学能力", "工程结构力学类合并", "confirmed"
    if has(a, "材料|焊接材料|成型|腐蚀|防腐") and not has(a, "船舶|海洋|海工|水产|食品"):
        return "材料工程能力", "材料工程类合并", "confirmed"
    if has(a, "环境工程|环境规划|环境管理|环境保护|固体废物|废弃物|废水|废气|污染治理|环保工程|土壤.*修复|地下水保护") and not has(a, "海洋|港口|船舶"):
        return "环境工程治理能力", "环境工程治理类合并", "confirmed"
    if has(a, "电子|电路|电气|PLC|自动化|控制系统|通信|信号|微波|FPGA|单片机|传感器|信息系统|光电|声信息|测控技术|智能仪表|微控制器|机器视觉") and not has(a, "船舶|轮机|海洋|港口|航运|海上风电|水产"):
        return "电子信息与自动化能力", "电子信息自动化类合并", "confirmed"
    if has(a, "能源动力|能源与动力|动力机械|内燃机|热能|制冷|低温|空调|热工") and not has(a, "船舶|轮机|海洋|海上风电"):
        return "能源动力工程能力", "能源动力类合并", "confirmed"
    if has(a, "生物化学|分子生物|细胞|基因|微生物|蛋白") and not has(a, "海洋|水产|渔业"):
        return "生物技术基础能力", "生物技术基础类合并", "confirmed"
    if has(a, "食品|农产品加工|质量安全") and not has(a, "水产|海洋"):
        return "食品工程质量能力", "食品工程质量类合并", "confirmed"
    if has(a, "无损检测|质量.*管控|质量.*改进|体系认证|合规管理|研制流程合规|标准化设计文档|技术文件审核") and not has(a, "船舶|海洋|海上|港口"):
        return "质量检测与合规管理能力", "质量检测合规类合并", "confirmed"
    if has(a, "教材|教师|双师型|教学"):
        return "教育教学能力", "教育教学类合并", "confirmed"
    if has(a, "劳动精神|工匠精神"):
        return "工程伦理责任能力", "职业精神类合并", "confirmed"

    # 海上风电与海洋能源
    if has(a, "海上风电|漂浮式风电|风资源|升压站|风电工程"):
        if has(a, "平台|场群|算法|软件|程序|系统开发|仿真程序|核心算法"):
            return "海上风电平台研发能力", "海上风电平台与算法研发合并", "confirmed"
        if has(a, "变压器|电气|并网|柔直|输电|电力系统|功率模块|电气系统"):
            return "海上风电电气系统能力", "海上风电电气系统类合并", "confirmed"
        if has(a, "物流|运输|安装运输|成本建模"):
            return "海上风电物流运输能力", "海上风电物流运输类合并", "confirmed"
        if has(a, "市场|商务|订单|政策|规划|成本|售前"):
            return "海上风电商务规划能力", "海上风电商务规划类合并", "confirmed"
        return "海上风电工程能力", "海上风电工程全流程合并", "confirmed"
    if has(a, "海洋能|可再生能源|潮流能|波浪能|漂浮式光伏|水面光伏|系泊|锚固"):
        return "海洋能源工程能力", "海洋能源工程类合并", "confirmed"
    if has(a, "LNG|接收站|甲醇|油气|能源转换|储能|新能源|海上能源|光伏电站") and not has(a, "船舶|航运"):
        return "涉海能源工程能力", "涉海能源类合并", "tentative"

    # 船舶与海工装备
    if has(a, "船舶|轮机|船体|舾装|管系|机舱|柴油机|船级社|船厂|造船|修船|单船|船员|水手|游艇|公务船|巡逻船|海工船|挖泥船"):
        if has(a, "船员证书|船员服务|船员管理系统|签证办理|船员派遣"):
            return "船员服务管理能力", "船员服务管理类合并", "confirmed"
        if has(a, "航运|租船|船舶代理|买卖|经纪|船务|调度|港口作业|配载|靠泊|靠离泊|进出港|出入境|进出境|联检|船代|单证|申报|货运|积载|装载|装卸|船舶贸易|船舶市场|船舶运营|船舶操作管理"):
            return "航运业务管理能力", "船舶相关航运业务合并", "confirmed"
        if has(a, "海务|机务|船舶管理|安全|应急|防污染|环保|消防|事故|HSE|合规|规章|法规|审验|检查|运营管理|维护管理|驾驶|操纵|航行|值班|避碰|甲板|水手|船长|船员管理"):
            return "船舶运营管理能力", "船舶运营管理类合并", "confirmed"
        if has(a, "网络安全|信息系统|数据中心|工业互联网|局域网|通信|通讯|导航|定位|电子海图|雷达|SCADA|软件|嵌入式|协议|信号|数字化|仿真"):
            return "船舶智能通导信息系统能力", "船舶通导与信息系统类合并", "confirmed"
        if has(a, "电气|电力|自动化|电子电气|电机|三电|电源|变频|控制器|推进系统|电控|报警|内通|火警"):
            return "船舶电气工程能力", "船舶电气工程类合并", "confirmed"
        if has(a, "轮机|机舱|动力|动力装置|柴油机|主机|辅机|通风空调|轴系|燃油|机械设备"):
            return "船舶轮机工程能力", "船舶轮机工程类合并", "confirmed"
        if has(a, "管系|配管|管路"):
            return "船舶管系工程能力", "船舶管系工程类合并", "confirmed"
        if has(a, "设备|维修|维护|维保|保养|故障诊断|管用养修"):
            return "船舶设备运维能力", "船舶设备运维类合并", "confirmed"
        if has(a, "涂装|焊接|分段|建造|制造|装配|生产|工艺|机械加工|加工|施工|安装|质量|检验|无损检测|探伤|调试|交付|项目管理|精益|监造|修理|坞修"):
            return "船舶建造制造能力", "船舶建造制造类合并", "confirmed"
        if has(a, "设计|结构|船体|舾装|外观|内装|总体|性能|稳性|三维|建模|NAPA|放样|制图|研发设计"):
            return "船舶设计能力", "船舶设计类合并", "confirmed"
        if has(a, "商务|市场|销售|客户|合同|风险|采购|供应链|产品推广|售后|技术支持|经营|报价|租赁|融资|资产|财务|费用|物资"):
            return "船舶商务供应链能力", "船舶商务供应链类合并", "confirmed"
        if has(a, "新能源|绿色船舶|智能船舶|无人船|大数据"):
            return "智能绿色船舶技术能力", "智能绿色船舶技术类合并", "confirmed"
        if has(a, "船舶与海洋工程|船舶工程|复杂工程|工程知识|问题分析|研究|实践|专业基础|总体认知"):
            return "船舶与海洋工程基础能力", "船舶海洋工程基础与综合分析类合并", "confirmed"
        return "船舶综合工程能力", "船舶相关但模块不明，暂作综合项", "tentative"
    if has(a, "海工"):
        if has(a, "商务|市场|客户|合同|销售"):
            return "海工装备商务管理能力", "海工商务类合并", "confirmed"
        if has(a, "施工|项目管理|现场|安装|建造|生产|质量|检验|工艺|涂装|焊接|交付"):
            return "海工装备建造管理能力", "海工建造管理类合并", "confirmed"
        if has(a, "设计|研发|结构|装备|产品"):
            return "海工装备设计研发能力", "海工设计研发类合并", "confirmed"
        return "海工装备工程能力", "海工装备综合能力", "tentative"
    if has(a, "海洋工程|海洋平台|海洋装备|海洋机电液|海上平台|FPSO|海底管道|疏浚管线|上部模块|水下|浮体|动态缆|柔性管缆|海洋管缆|脐带缆|海上工程|海上施工|海上作业|海上吊装"):
        if has(a, "项目|管理|分包|界面|变更|成本|进度|计划|流程|预警|市场"):
            return "海洋工程项目管理能力", "海洋工程项目管理类合并", "confirmed"
        if has(a, "测绘|测量|勘测|勘察|地质|地球物理"):
            return "海洋工程勘测测绘能力", "海洋工程勘测测绘类合并", "confirmed"
        if has(a, "结构|力学|平台|FPSO|上部模块|海底管道|管道|管线|配管|电仪|设计|研发"):
            return "海洋工程结构装备能力", "海洋工程结构装备类合并", "confirmed"
        if has(a, "建造|生产|工艺|施工|安装|质量|运维|设备|装备"):
            return "海洋装备建造运维能力", "海洋装备建造运维类合并", "confirmed"
        return "海洋工程装备能力", "海洋工程装备综合能力", "tentative"

    # 港口、港航与航运物流
    if has(a, "港口|港航|航道|水运|码头|海岸|近海工程|岸电|门机|起重|堆场"):
        if has(a, "机械|机电|电气|岸电|起重|门机|供配电|设备|传动|变频器|维修|运维|安装调试"):
            return "港口机电设备能力", "港口机电设备类合并", "confirmed"
        if has(a, "智慧|智能|信息化|DICT|物联网|识别|平台|解决方案|算法|系统|无人港口"):
            return "智慧港口技术能力", "智慧港口技术类合并", "confirmed"
        if has(a, "物流|操作|堆场|库场|件杂货|散货|业务|支干航线|订舱|船舶调度|配载|仓储"):
            return "港口物流业务能力", "港口物流业务类合并", "confirmed"
        if has(a, "安全|应急|生产体系|事故"):
            return "港口安全管理能力", "港口安全类合并", "confirmed"
        return "港口航道工程能力", "港口航道工程类合并", "confirmed"
    if has(a, "海事"):
        if has(a, "法|危防|调查|公共管理|监管|海域使用|保险|贸易"):
            return "海事法律监管能力", "海事法律监管类合并", "confirmed"
        return "海事管理能力", "海事管理类合并", "confirmed"
    if has(a, "航海|GMDSS|无线电导航|北斗|卫星导航"):
        if has(a, "智能|算法|系统|数字|信息|解决方案"):
            return "智能航海技术能力", "智能航海技术类合并", "confirmed"
        if has(a, "通信|导航|GMDSS|仪器|雷达|电子海图"):
            return "航海通信导航能力", "航海通信导航类合并", "confirmed"
        if has(a, "气象|海洋学|水文"):
            return "航海气象海洋应用能力", "航海气象海洋应用类合并", "confirmed"
        return "航海技术能力", "航海技术类合并", "confirmed"
    if has(a, "航运|海运|远洋|租船|货代|多式联运|运输代理|航线|船东|船代|外贸单证|干散货|油轮"):
        if has(a, "数据|信息系统|物联网|智能|科技"):
            return "智慧航运技术能力", "智慧航运技术类合并", "confirmed"
        if has(a, "法律|法规|政策|保险|合同"):
            return "航运法律商务能力", "航运法律商务类合并", "confirmed"
        if has(a, "物流|供应链|货代|多式联运|运输"):
            return "航运物流管理能力", "航运物流类合并", "confirmed"
        return "航运业务管理能力", "航运业务管理类合并", "confirmed"

    # 海洋科学、环境、数据与智能
    if has(a, "水声|声学|声呐|声场"):
        return "水声海洋声学能力", "水声海洋声学类合并", "confirmed"
    if has(a, "海洋环境|环境监测|生态环境|环境评价|污染|水质|生态调查|生态保护"):
        return "海洋环境监测评价能力", "海洋环境监测评价类合并", "confirmed"
    if has(a, "海洋调查|海洋观测|海洋测量|海洋仪器|海洋传感|探测|遥感|卫星海洋"):
        return "海洋调查观测能力", "海洋调查观测类合并", "confirmed"
    if has(a, "海洋测绘|海洋地理信息|海洋GIS"):
        return "海洋测绘地理信息能力", "海洋测绘地理信息类合并", "confirmed"
    if has(a, "物理海洋|海洋动力|大气海洋|海洋数值|海洋气象|气象海洋|数值模拟|HPC"):
        return "物理海洋与气象分析能力", "物理海洋气象类合并", "confirmed"
    if has(a, "海洋化学|化学海洋|海水分析|地球化学"):
        return "海洋化学分析能力", "海洋化学类合并", "confirmed"
    if has(a, "海洋地质|地球物理|海底|矿产|地貌|古海洋"):
        return "海洋地质地球物理能力", "海洋地质地球物理类合并", "confirmed"
    if has(a, "海洋生物|浮游|底栖|微藻|藻类|生物海洋|海洋生态"):
        return "海洋生物生态能力", "海洋生物生态类合并", "confirmed"
    if has(a, "海洋馆|海洋动物|海洋生物健康|保育"):
        return "海洋生物保育管理能力", "海洋生物保育管理类合并", "confirmed"
    if has(a, "海洋信息|数字海洋|智慧海洋|海洋数据|海洋软件|海洋人工智能|海洋智能|海洋地理信息|海洋GIS|海洋大数据|海洋系统架构|海洋.*通信|海洋.*算法|海洋.*AI|海洋电子|海洋测控|海洋无人|海洋时空数据|海洋仪表|海洋前沿技术"):
        return "海洋信息智能技术能力", "海洋信息智能技术类合并", "confirmed"
    if has(a, "海洋材料|海洋.*高分子|绳网材料"):
        return "海洋材料工程能力", "海洋材料工程类合并", "confirmed"
    if has(a, "海洋药物|海洋生命科学"):
        return "海洋生物医药能力", "海洋生物医药类合并", "confirmed"
    if has(a, "海洋实验|海洋实践|海洋实习|海洋学科竞赛|海洋科技实践|海洋技术综合|海洋技术专业知识"):
        return "海洋科学研究能力", "海洋科学实践研究类合并", "confirmed"
    if has(a, "海洋科学|海洋交叉|海洋专业|海洋资源|海洋基础|海洋研究"):
        return "海洋科学研究能力", "海洋科学研究类合并", "confirmed"

    # 水产与渔业
    if has(a, "水产|养殖|渔业|对虾|鱼类|贝类|苗种|病害|饲料|营养|动保|水生|增殖"):
        if has(a, "疾病|病害|防控|诊断|免疫|微生物"):
            return "水产病害防控能力", "水产病害防控类合并", "confirmed"
        if has(a, "育种|遗传|苗种|繁育|种质"):
            return "水产生物育种繁育能力", "水产生物育种繁育类合并", "confirmed"
        if has(a, "饲料|营养"):
            return "水产营养饲料能力", "水产营养饲料类合并", "confirmed"
        if has(a, "加工|食品|质量|检测|采购"):
            return "水产品加工质量能力", "水产品加工质量类合并", "confirmed"
        if has(a, "设施|智慧|自动化|设备|信息技术"):
            return "智慧水产养殖能力", "智慧水产养殖类合并", "confirmed"
        if has(a, "服务|推广|销售|产品|方案"):
            return "水产养殖技术服务能力", "水产技术服务类合并", "confirmed"
        return "水产养殖技术能力", "水产养殖技术类合并", "confirmed"

    # 交通运输、土木、水利等邻近支撑
    if has(a, "交通运输|交通工程|交通土建|交通基础设施|交通规划|智慧交通|运输工程|道路|桥梁|土木|岩土|地下工程"):
        return "交通土建工程能力", "交通土建工程类合并", "confirmed"
    if has(a, "水利水电|水文|水资源|水工"):
        return "水利水文工程能力", "水利水文工程类合并", "confirmed"
    if has(a, "物流|供应链|仓储|采购|运输方案"):
        return "物流供应链管理能力", "物流供应链类合并", "confirmed"
    if has(a, "地球科学|地质|地震|地层|岩矿|沉积盆地"):
        return "地质地球科学能力", "地质地球科学类合并", "confirmed"
    if has(a, "大气|气象|天气|气候"):
        return "大气气象分析能力", "大气气象类合并", "confirmed"
    if has(a, "化学分析|化学实验|化学学科|药学|化学电源"):
        return "化学实验分析能力", "化学实验分析类合并", "confirmed"
    if has(a, "安全|应急|风险|消防|救助|救捞|打捞"):
        return "安全应急管理能力", "安全应急类合并", "tentative"
    if has(a, "英语|英文|外语|双语"):
        return "外语应用能力", "外语应用类合并", "confirmed"
    if has(a, "法律|法规|执法|政策"):
        return "法律政策应用能力", "法律政策类合并", "confirmed"

    # Fallback: preserve the original but mark for review.
    return ensure_ability(a), "未纳入稳定宽口径规则，保留原名待复核", "needs_user_review"


def source_balance(supply, demand):
    if supply and demand:
        return "双端共有"
    if supply > demand:
        return "供给主导"
    if demand > supply:
        return "需求主导"
    return "低频待复核"


def write_csv(path, rows, fieldnames):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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
        canonical, rationale, status = code_ability(row["original_ability"])
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
        status_counts = {r["coding_status"] for r in rows}
        if "needs_user_review" in status_counts:
            dict_status = "含待复核项"
        elif "tentative" in status_counts:
            dict_status = "含暂定项"
        else:
            dict_status = "confirmed"
        dictionary.append({
            "canonical_competency": canonical,
            "original_ability_count": len(rows),
            "supply_occurrences": supply,
            "demand_occurrences": demand,
            "source_balance": source_balance(supply, demand),
            "dictionary_status": dict_status,
            "original_ability_examples": " | ".join(r["original_ability"] for r in rows[:12]),
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
    dict_status_counts = defaultdict(int)
    for row in dictionary:
        dict_status_counts[row["dictionary_status"]] += 1

    notes = f"""# 供需能力开放编码审计说明（中观偏上，全量）

本轮按 `marine-competency-open-coding` skill 执行：不调用外部 API，不预设规范技能数量，不预设类别体系。脚本仅用于本地读写、计数和把已确认的宽口径审计规则应用到全量 ability。

## 规模

- 原始唯一 ability：{len(inventory)}
- 供给端明细：{len(supply_rows)}
- 需求端明细：{len(demand_rows)}
- 归纳规范技能：{len(dictionary)}

## 编码状态

- confirmed：{status_counts['confirmed']}
- tentative：{status_counts['tentative']}
- needs_user_review：{status_counts['needs_user_review']}

## 口径

- 采用中观偏上口径，规范技能一般对应二级专业模块。
- 同一对象下的设计、施工、安装、调试、检验、运维、质量控制、管理等动作，原则上合并。
- 保留不同二级专业模块边界，例如 `船舶电气工程能力`、`船舶轮机工程能力`、`船舶设计能力`、`船舶建造制造能力` 不合并为笼统的船舶工程能力。

## 主要宽口径合并

- 船舶电气设计、调试、质量检验、自动化控制 -> 船舶电气工程能力
- 船舶轮机设计、管理、质量检验、机舱资源管理 -> 船舶轮机工程能力
- 船体、结构、舾装、总体、外观设计 -> 船舶设计能力
- 船舶建造项目、分段生产、机械加工、柴油机制造、产品质量检验 -> 船舶建造制造能力
- 港口航道设计、施工、项目管理、水运工程设计 -> 港口航道工程能力
- 海上风电项目管理、施工管理、安全管理 -> 海上风电工程能力

## 后续复核建议

- 优先人工复核 `needs_user_review` 和 `tentative` 行。
- 对高频规范技能检查是否仍过宽或过窄。
- 若论文需要更高一致性，可在此表基础上进行第二轮人工合并。
"""
    (OUTPUT_DIR / "open_coding_audit_notes.md").write_text(notes, encoding="utf-8")

    print(f"inventory={len(inventory)}")
    print(f"canonical_competencies={len(dictionary)}")
    print(f"supply_rows={len(supply_rows)}")
    print(f"demand_rows={len(demand_rows)}")
    print("mapping_status=" + json.dumps(dict(status_counts), ensure_ascii=False))
    print("dictionary_status=" + json.dumps(dict(dict_status_counts), ensure_ascii=False))
    print(f"output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()
