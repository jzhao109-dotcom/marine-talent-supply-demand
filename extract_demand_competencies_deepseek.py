#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SYSTEM_PROMPT = """你是海洋产业人才需求端能力抽取专家。
你的任务是从招聘岗位文本中抽取“需求端能力”，用于后续与高校培养方案供给端能力做匹配。

核心目标：
1. 抽取的 ability 应优先呈现海洋产业语境，尽量带有“海洋、船舶、港航、航运、海工、海上风电、港口、水产、海洋环境、海洋数据”等语义锚点。
2. 不要把职位描述中的每个动作、工具、证书、行政事项都拆成独立能力；要归并为可与高校培养能力匹配的中观能力。
3. 对 UI、软件、电气、管理、商务、质量、数据分析等通用技能，只有在原文存在涉海岗位场景时，才抽取为“涉海场景 + 通用技能”的中观能力。
4. 宁可少抽，也不要多抽。不能为了保留通用能力而简单添加“海洋/船舶”前缀。

只输出合法 JSON object，格式必须严格如下：
{
  "records": [
    {
      "source_index": 123,
      "items": [
        {
          "ability": "能力短语",
          "evidence": "原文证据"
        }
      ]
    }
  ]
}

字段要求：
1. source_index：必须原样返回输入记录中的 source_index。
2. ability：从职位描述中归纳出的中观能力单元，必须是中文短语，尽量 6-18 个汉字，以“xxx能力”结尾。
3. evidence：必须摘取或紧贴职位描述原文，不要编造；应能直接支撑 ability，尽量 20-100 个汉字。
4. 每个 item 只能包含 ability 和 evidence 两个字段；不要输出技能领域、置信度、解释或其他字段。

抽取依据：
1. 主要依据“职位描述”，包括岗位职责、任职资格、技能要求、工作内容、项目经验要求。
2. 可参考“招聘岗位”和“职业名称”理解上下文，但不要仅凭岗位名臆造能力。
3. 公司简介、薪资福利、年龄限制、学历、证书、品行描述等不是能力，除非它们明确对应职业技能或资质能力。

颗粒度要求：
1. 使用“中观”尺度。ability 应对应一个海洋相关技术领域、业务模块、专业能力或复合能力，而不是单个动作。
2. 先识别岗位中的主要涉海业务模块，再抽能力；一个业务模块内的规划、设计、开发、施工、运维、检查、培训、文件、沟通等动作，优先合并为一条中观能力。
3. 不要把支撑动作单独写成能力，例如“图纸识别能力、人员培训能力、体系文件修订能力、证件办理能力、沟通协作能力、软件操作能力”一般不要单独输出；应并入“船舶电气工程能力、船舶海务管理能力、船员服务管理能力、海洋仿真产品设计能力”等中观能力。
4. 也不要过于宏观，例如不要只写“工程能力”“管理能力”“设计能力”“软件开发能力”；需要保留涉海领域限定。
5. 合适颗粒度示例：
   - “参与海上风电场群规划设计业务、平台研发、核心算法研发”可抽为“海上风电规划设计能力”“海上风电平台研发能力”“海上风电算法研发能力”。
   - “船舶电气工程施工、识别电气施工图纸、安装测试控制系统、现场调试指导”可抽为“船舶电气工程能力”“船舶电气调试能力”。
   - “负责海洋环境仿真高保真界面设计、用户界面设计、交互流程优化”可抽为“海洋仿真产品设计能力”。
   - “全面负责分管船舶海务管理、航行计划、访船检查、PSC/FSC预检、船岸应急”可抽为“船舶海务管理能力”“船舶安全检查能力”“船岸应急管理能力”。
   - “办理船员签证、外籍证书、船员系统内容输入”可抽为“船员服务管理能力”，不要拆成证件办理、系统操作。
   - “熟悉C/C++/Java至少一门语言”只有在岗位是海上风电平台、海洋数据、智能航运等场景时，才抽为“海洋平台软件开发能力”或相近能力。
6. 避免把 ability 命名为“某某设计审图能力、某某图纸识别能力、某某施工安装能力、某某系统操作能力、某某证件办理能力、某某面试培训能力”等动作型能力；优先合并为“船舶电气工程能力、船舶电气施工运维能力、船员适任管理能力、船员服务管理能力”等业务型能力。
7. 如果一个岗位只有若干支撑动作服务于同一业务模块，只输出一个合并后的中观 ability。例如 UI、视觉、交互、规范制定共同服务于海洋仿真产品时，只输出“海洋仿真产品设计能力”。

优先抽取：
1. 海洋、船舶、港航、海工装备、海洋能源、海洋生态、水产养殖、海洋数据、智能航运、港口物流等直接涉海能力。
2. 数字技术、工程设计制造、检测运维、项目管理、质量管理、商务管理等支撑能力，只有能与具体涉海业务场景合并命名时才抽取。
3. 对可迁移能力，如团队协作、沟通交流、客户支持、英语应用、常用软件操作等，通常不单独抽取；只有当其构成涉海业务模块的关键能力时，才并入中观能力。

去噪规则：
1. 不抽取学历、经验年限、年龄、薪资、工作地点、招聘人数、福利待遇。
2. 不抽取“吃苦耐劳、品行端正、责任心强、身体健康”等泛化素质。
3. 不抽取纯行政执行事项、证件手续、文件收集、会议沟通、人员培训、普通办公软件、设计软件操作等低层次事项，除非它们可以上升为涉海业务中观能力。
4. ability 不要写成完整句子，不要包含“掌握/熟悉/能够/负责”等句式开头，优先写成名词性能力短语。
5. 合并同义重复项；不要把同一岗位模块拆成多个过细能力。
6. 输出前自检并删除以下不合格项：
   - ability 仅是通用技能、工具、行政流程或个人素质。
   - ability 以“用户界面、视觉设计、交互优化、设计规范、设计审图、图纸识别、施工安装、系统操作、证件办理、签证办理、文件修订、技术支持、面试、培训、沟通、英语、软件操作”为核心。
   - ability 可以并入同一记录中的更大涉海业务模块。
7. 每条记录通常返回 1-4 条 items，复杂岗位最多 6 条。若职位描述无法支持具体涉海或涉海支撑能力，可以返回空数组。
8. 必须为每条输入记录返回一个 records 元素，不要遗漏 source_index。
9. 不要使用 Markdown，不要输出 JSON 以外的任何文字。
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract demand-side competencies from job descriptions with DeepSeek."
    )
    parser.add_argument("--input-file", default="marine_competency_mapped_8class_merged.jsonl")
    parser.add_argument("--output-dir", default="需求端_DeepSeek能力提取_flash_当前prompt")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-batch-chars", type=int, default=60000)
    parser.add_argument("--max-output-tokens", type=int, default=6000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N records.")
    parser.add_argument("--force", action="store_true", help="Re-run batches already present in output JSONL.")
    parser.add_argument("--no-thinking", action="store_true", default=True)
    return parser.parse_args()


def normalize_text(text):
    text = str(text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_json_loads(content):
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def read_records(path, limit=0):
    records = []
    with Path(path).open("r", encoding="utf-8") as f:
        for row_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            obj["_row_number"] = row_number
            records.append(obj)
            if limit and len(records) >= limit:
                break
    return records


def record_text(record):
    parts = [
        f"source_index: {record.get('source_index')}",
        f"招聘岗位: {record.get('招聘岗位') or ''}",
        f"职业名称: {record.get('occupation_name') or ''}",
        f"上市公司行业: {record.get('上市公司行业') or ''}",
        f"学历要求: {record.get('学历要求') or ''}",
        f"要求经验: {record.get('要求经验') or ''}",
        "职位描述:",
        normalize_text(record.get("职位描述") or ""),
    ]
    return "\n".join(parts).strip()


def make_batches(records, batch_size, max_batch_chars):
    batches = []
    current = []
    current_chars = 0
    for record in records:
        text = record_text(record)
        text_len = len(text)
        if current and (len(current) >= batch_size or current_chars + text_len > max_batch_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(record)
        current_chars += text_len
    if current:
        batches.append(current)
    return batches


def call_deepseek(api_key, base_url, model, batch_id, records, max_tokens, no_thinking):
    url = base_url.rstrip("/") + "/chat/completions"
    payload_records = []
    for record in records:
        payload_records.append({
            "source_index": record.get("source_index"),
            "招聘岗位": record.get("招聘岗位") or "",
            "occupation_name": record.get("occupation_name") or "",
            "职位描述": normalize_text(record.get("职位描述") or ""),
        })

    user_prompt = f"""请从以下招聘岗位记录中抽取需求端能力。
必须为每个 source_index 返回一个 records 元素；每条 item 只能有 ability 和 evidence 两个字段。

batch_id: {batch_id}

岗位记录：
{json.dumps(payload_records, ensure_ascii=False)}
"""

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
        "stream": False,
    }
    if no_thinking:
        body["thinking"] = {"type": "disabled"}

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    last_error = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                response_payload = json.loads(resp.read().decode("utf-8"))
            message = response_payload["choices"][0]["message"]
            content = message.get("content") or ""
            parsed = safe_json_loads(content)
            return {
                "ok": True,
                "parsed": parsed,
                "usage": response_payload.get("usage", {}),
            }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {exc.code}: {detail[:1000]}"
            if exc.code in (400, 401, 403):
                break
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(min(2 ** attempt, 20))
    return {"ok": False, "error": last_error}


def append_jsonl(path, rows):
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_done_batches(jsonl_path):
    done = set()
    if not jsonl_path.exists():
        return done
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("ok"):
                done.add(row.get("batch_id"))
    return done


def flatten_to_csv(batch_jsonl_path, items_csv_path, summary_csv_path, source_records):
    by_source_index = {}
    source_order = []
    for record in source_records:
        key = str(record.get("source_index"))
        if key not in by_source_index:
            by_source_index[key] = record
            source_order.append(key)

    item_rows = []
    seen_items = set()
    summary = {
        key: {"items": 0, "errors": 0, "batches": 0}
        for key in source_order
    }

    with batch_jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            for source_index in row.get("source_indexes", []):
                key = str(source_index)
                if key in summary:
                    summary[key]["batches"] += 1
            if not row.get("ok"):
                for source_index in row.get("source_indexes", []):
                    key = str(source_index)
                    if key in summary:
                        summary[key]["errors"] += 1
                continue

            parsed_records = (row.get("parsed") or {}).get("records") or []
            for parsed_record in parsed_records:
                source_index = parsed_record.get("source_index")
                key = str(source_index)
                if key not in by_source_index:
                    continue
                record = by_source_index[key]
                items = parsed_record.get("items") or []
                for item in items:
                    ability = item.get("ability", "")
                    evidence = item.get("evidence", "")
                    dedupe_key = (key, ability, evidence)
                    if dedupe_key in seen_items:
                        continue
                    seen_items.add(dedupe_key)
                    summary[key]["items"] += 1
                    item_rows.append({
                        "source_index": record.get("source_index", source_index),
                        "招聘岗位": record.get("招聘岗位", ""),
                        "occupation_name": record.get("occupation_name", ""),
                        "ability": ability,
                        "evidence": evidence,
                    })

    with items_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["source_index", "招聘岗位", "occupation_name", "ability", "evidence"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(item_rows)

    with summary_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["source_index", "招聘岗位", "occupation_name", "items", "errors", "batches"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key in source_order:
            record = by_source_index[key]
            writer.writerow({
                "source_index": record.get("source_index", key),
                "招聘岗位": record.get("招聘岗位", ""),
                "occupation_name": record.get("occupation_name", ""),
                **summary[key],
            })


def main():
    args = parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Missing DEEPSEEK_API_KEY in environment.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_jsonl_path = output_dir / "demand_competency_batches.jsonl"
    items_csv_path = output_dir / "demand_competency_items.csv"
    summary_csv_path = output_dir / "demand_competency_record_summary.csv"

    records = read_records(args.input_file, args.limit)
    batches = make_batches(records, args.batch_size, args.max_batch_chars)
    batch_tasks = []
    for idx, batch in enumerate(batches, start=1):
        batch_id = f"batch_{idx:05d}"
        batch_tasks.append((batch_id, batch))

    done = set() if args.force else load_done_batches(batch_jsonl_path)
    batch_tasks = [(batch_id, batch) for batch_id, batch in batch_tasks if batch_id not in done]
    print(f"Records: {len(records)} | pending batches: {len(batch_tasks)} | output: {output_dir}", flush=True)

    def run_task(batch_id, batch):
        result = call_deepseek(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            batch_id=batch_id,
            records=batch,
            max_tokens=args.max_output_tokens,
            no_thinking=args.no_thinking,
        )
        row = {
            "batch_id": batch_id,
            "source_indexes": [record.get("source_index") for record in batch],
            "ok": result["ok"],
        }
        if result["ok"]:
            row["parsed"] = result["parsed"]
            row["usage"] = result.get("usage", {})
        else:
            row["error"] = result.get("error")
        return row

    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(run_task, batch_id, batch) for batch_id, batch in batch_tasks]
        for future in as_completed(futures):
            row = future.result()
            append_jsonl(batch_jsonl_path, [row])
            completed += 1
            status = "ok" if row.get("ok") else "err"
            print(f"[{completed}/{len(batch_tasks)}] {status} {row['batch_id']}", flush=True)

    if batch_jsonl_path.exists():
        flatten_to_csv(batch_jsonl_path, items_csv_path, summary_csv_path, records)
        print(f"Wrote: {batch_jsonl_path}")
        print(f"Wrote: {items_csv_path}")
        print(f"Wrote: {summary_csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
