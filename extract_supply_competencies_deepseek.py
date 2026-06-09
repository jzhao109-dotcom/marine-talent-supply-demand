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


SYSTEM_PROMPT = """你是海洋产业人才供给端能力抽取专家。
你的任务是从高校/高职培养方案文本中抽取“供给端能力”，用于后续与招聘需求端能力做匹配。

只输出合法 JSON object，格式必须严格如下：
{
  "items": [
    {
      "ability": "能力短语",
      "evidence": "原文证据"
    }
  ]
}

字段要求：
1. ability：从原文归纳出的中观能力单元，必须是中文短语，尽量 6-18 个汉字。
2. evidence：必须摘取或紧贴原文，不要编造；应能直接支撑 ability，尽量 20-100 个汉字。
3. 每条 item 只能包含 ability 和 evidence 两个字段，不要输出学校、专业、领域、课程类型、置信度、解释或其他字段。

颗粒度要求：
1. 使用“中观”尺度。ability 应对应一个专业方向、能力模块、技术领域或复合能力，而不是单个动作。
2. 不要把同一领域内的勘测、规划、设计、施工、运行、管理、科研等动作分别拆成多条；如果原文把它们作为同一专业培养方向描述，应合并为一条。
3. 也不要过于宏观，例如不要只写“工程能力”“科研能力”“创新能力”；需要保留领域限定。
4. 合适颗粒度示例：
   - “水利水电工程勘测规划能力”“水利水电工程设计能力”“水利水电工程施工组织能力”“水利水电工程运行管理能力”应合并为“水利水电工程能力”。
   - “海洋调查仪器操作能力”“海洋调查实习能力”“海洋数据采集能力”可合并为“海洋调查观测能力”。
   - “船舶结构设计能力”“船舶性能分析能力”“船舶总体设计能力”可合并为“船舶设计分析能力”。
   - “水文信息采集能力”“水文预报能力”“水文统计分析能力”可合并为“水文水资源分析能力”。
5. 如果一个专业文本覆盖多个清晰方向，可以输出多条中观能力；但每条都应覆盖一组相关知识/课程/实践，而不是一个孤立课程名。

抽取范围：
1. 优先从“培养目标、毕业要求、毕业生能力要求、核心课程、特色课程、实践环节、专业方向、课程体系说明”中抽取。
2. 课程名可以转化为能力，但 evidence 中必须保留课程名或相邻原文。例如“海洋调查仪器操作”可抽为“海洋调查仪器操作能力”。
3. 对海洋、船舶、港航、海工装备、海洋能源、海洋生态、水产养殖、海洋数据、智能航运、港口物流等能力要优先保留。
4. 对数字技术、工程设计制造、检测运维、项目管理等支撑能力，只有当它们出现在专业培养目标、毕业要求、专业课程或实践环节中时才抽取。

去噪规则：
1. 不抽取思想政治、体育、军训、心理健康、纯学分、纯学制、课程代码、先修课程、推荐学期等行政信息。
2. 不抽取空泛人格品质，除非原文明确对应可迁移能力，如“团队协作能力”“跨文化沟通能力”“工程伦理意识”。
3. 合并同义重复项；不要把同一专业方向、同一毕业要求或同一组课程拆成多个过细能力。
4. ability 不要写成完整句子，不要包含“掌握/具备/了解/能够”等句式开头，优先写成名词性能力短语。
5. evidence 不要超过 120 个汉字；如原文太长，请截取最能支撑能力的核心片段。
6. 每个 chunk 最多返回 35 条 items。若文本信息很少，可以返回空数组。
7. 不要使用 Markdown，不要输出 JSON 以外的任何文字。
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract supply-side competencies from curriculum txt files with DeepSeek V4 Pro."
    )
    parser.add_argument("--input-dir", default="主分析_141份_含港航物流与邻近支撑")
    parser.add_argument("--output-dir", default="供给端_DeepSeek能力提取_141份_ability_evidence")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--chunk-chars", type=int, default=120000)
    parser.add_argument("--overlap-chars", type=int, default=3000)
    parser.add_argument("--max-output-tokens", type=int, default=6000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N files.")
    parser.add_argument("--force", action="store_true", help="Re-run chunks already present in the output JSONL.")
    parser.add_argument("--no-thinking", action="store_true", default=True)
    return parser.parse_args()


def read_text(path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def normalize_text(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def split_text(text, max_chars, overlap_chars):
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind("\n[Page "), window.rfind("。"))
            if cut > max_chars * 0.65:
                end = start + cut + 1
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(0, end - overlap_chars)
    return [chunk for chunk in chunks if chunk]


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


def call_deepseek(api_key, base_url, model, file_name, chunk_index, chunk_count, text, max_tokens, no_thinking):
    url = base_url.rstrip("/") + "/chat/completions"
    user_prompt = f"""请从以下培养方案文本 chunk 中抽取供给端能力。
只返回 JSON object，且每条 item 只能有 ability 和 evidence 两个字段。

文件名：{file_name}
chunk：{chunk_index + 1}/{chunk_count}

文本：
<<<
{text}
>>>"""
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
                payload = json.loads(resp.read().decode("utf-8"))
            message = payload["choices"][0]["message"]
            content = message.get("content") or ""
            parsed = safe_json_loads(content)
            return {
                "ok": True,
                "parsed": parsed,
                "raw_content": content,
                "usage": payload.get("usage", {}),
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


def load_done_chunks(jsonl_path):
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
                done.add((row.get("source_file"), row.get("chunk_index")))
    return done


def append_jsonl(path, rows):
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def flatten_to_csv(jsonl_path, csv_path, summary_path):
    item_rows = []
    summary = {}
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            source_file = row.get("source_file", "")
            summary.setdefault(source_file, {"chunks": 0, "items": 0, "errors": 0})
            if not row.get("ok"):
                summary[source_file]["errors"] += 1
                continue
            summary[source_file]["chunks"] += 1
            parsed = row.get("parsed") or {}
            items = parsed.get("items") or parsed.get("competencies") or []
            summary[source_file]["items"] += len(items)
            for comp in items:
                item_rows.append({
                    "ability": comp.get("ability", ""),
                    "evidence": comp.get("evidence", ""),
                })

    fieldnames = ["ability", "evidence"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(item_rows)

    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source_file", "chunks", "items", "errors"])
        writer.writeheader()
        for source_file, stats in sorted(summary.items()):
            writer.writerow({"source_file": source_file, **stats})


def main():
    args = parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Missing DEEPSEEK_API_KEY in environment.", file=sys.stderr)
        return 2

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "supply_competency_chunks.jsonl"
    csv_path = output_dir / "supply_competency_items.csv"
    summary_path = output_dir / "supply_competency_file_summary.csv"

    files = sorted(input_dir.rglob("*.txt"))
    if args.limit:
        files = files[:args.limit]

    tasks = []
    for path in files:
        rel = str(path.relative_to(input_dir))
        text = normalize_text(read_text(path))
        chunks = split_text(text, args.chunk_chars, args.overlap_chars)
        for chunk_index, chunk in enumerate(chunks):
            tasks.append({
                "source_file": rel,
                "chunk_index": chunk_index,
                "chunk_count": len(chunks),
                "char_start_hint": max(0, chunk_index * (args.chunk_chars - args.overlap_chars)),
                "text": chunk,
            })

    done = set() if args.force else load_done_chunks(jsonl_path)
    tasks = [task for task in tasks if (task["source_file"], task["chunk_index"]) not in done]
    print(f"Files: {len(files)} | pending chunks: {len(tasks)} | output: {output_dir}", flush=True)

    def run_task(task):
        result = call_deepseek(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            file_name=task["source_file"],
            chunk_index=task["chunk_index"],
            chunk_count=task["chunk_count"],
            text=task["text"],
            max_tokens=args.max_output_tokens,
            no_thinking=args.no_thinking,
        )
        row = {
            "source_file": task["source_file"],
            "chunk_index": task["chunk_index"],
            "chunk_count": task["chunk_count"],
            "char_start_hint": task["char_start_hint"],
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
        futures = [executor.submit(run_task, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            append_jsonl(jsonl_path, [row])
            completed += 1
            status = "ok" if row.get("ok") else "err"
            print(f"[{completed}/{len(tasks)}] {status} {row['source_file']} chunk {row['chunk_index'] + 1}/{row['chunk_count']}", flush=True)

    if jsonl_path.exists():
        flatten_to_csv(jsonl_path, csv_path, summary_path)
        print(f"Wrote: {jsonl_path}")
        print(f"Wrote: {csv_path}")
        print(f"Wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
