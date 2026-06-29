# Policy Competency Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a DeepSeek API extraction script that infers policy-side marine talent abilities from OCR policy texts and outputs only `ability` and `evidence` items.

**Architecture:** Add one standalone script that mirrors the existing supply-side DeepSeek chunk workflow, but uses a policy-specific prompt and output schema. Keep pure text/JSON/CSV helpers testable without API access, then wire them into the CLI and DeepSeek call path.

**Tech Stack:** Python standard library (`argparse`, `csv`, `json`, `re`, `urllib`, `concurrent.futures`, `pathlib`), DeepSeek Chat Completions API, `unittest`.

---

## File Structure

- Create: `extract_policy_competencies_deepseek.py`
  - Reads OCR `.txt` policy files.
  - Removes extraction headers.
  - Splits long policy texts into overlapping chunks.
  - Calls DeepSeek with a policy-task inference prompt.
  - Writes restartable chunk JSONL and flattened CSV outputs.
- Create: `tests/test_policy_competency_extraction.py`
  - Imports the script as a module.
  - Tests pure helper behavior without network calls.
- Use existing input directory: `海洋人才政策（删减后）_OCR文本/海洋人才政策`
- Create runtime output directory when script runs: `政策端_DeepSeek能力推断_海洋人才政策`

## Task 1: Add Tests For Policy Extraction Helpers

**Files:**
- Create: `tests/test_policy_competency_extraction.py`

- [ ] **Step 1: Create the failing unit test file**

Create `tests/test_policy_competency_extraction.py` with this content:

```python
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "extract_policy_competencies_deepseek.py"
spec = importlib.util.spec_from_file_location("policy_extract", MODULE_PATH)
policy_extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy_extract)


class PolicyCompetencyExtractionTests(unittest.TestCase):
    def test_clean_policy_text_removes_ocr_headers(self):
        text = """源文件: 海洋人才政策（删减后）\\a.pdf
提取状态: ocr_extracted
OCR引擎: PaddleOCR
OCR渲染比例: 1.5
页数: 1
平均置信度: 0.9917
--- 第 1 页 ---
开展海洋生态环境整治修复技术研究。
"""

        cleaned = policy_extract.clean_policy_text(text)

        self.assertEqual(cleaned, "--- 第 1 页 ---\n开展海洋生态环境整治修复技术研究。")

    def test_split_text_uses_overlap_for_long_text(self):
        text = "第一段。" * 80 + "\n\n" + "第二段。" * 80

        chunks = policy_extract.split_text(text, max_chars=180, overlap_chars=20)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 220 for chunk in chunks))
        self.assertTrue(all(chunk.strip() for chunk in chunks))

    def test_safe_json_loads_accepts_markdown_wrapped_json(self):
        content = """```json
{"items":[{"ability":"海洋生态评估与修复能力","evidence":"开展海洋生态环境整治修复技术研究"}]}
```"""

        parsed = policy_extract.safe_json_loads(content)

        self.assertEqual(parsed["items"][0]["ability"], "海洋生态评估与修复能力")

    def test_normalize_items_keeps_only_ability_and_evidence(self):
        parsed = {
            "items": [
                {
                    "ability": "海洋生态评估与修复能力",
                    "evidence": "开展海洋生态环境整治修复技术研究",
                    "confidence": "high",
                },
                {"ability": "", "evidence": "无能力"},
                {"ability": "空证据能力", "evidence": ""},
            ]
        }

        items = policy_extract.normalize_items(parsed)

        self.assertEqual(
            items,
            [
                {
                    "ability": "海洋生态评估与修复能力",
                    "evidence": "开展海洋生态环境整治修复技术研究",
                }
            ],
        )

    def test_flatten_to_csv_writes_item_and_file_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jsonl_path = root / "chunks.jsonl"
            items_csv = root / "items.csv"
            summary_csv = root / "summary.csv"
            rows = [
                {
                    "source_file": "a.txt",
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "ok": True,
                    "parsed": {
                        "items": [
                            {
                                "ability": "海洋生态评估与修复能力",
                                "evidence": "开展海洋生态环境整治修复技术研究",
                                "confidence": "high",
                            }
                        ]
                    },
                },
                {
                    "source_file": "b.txt",
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "ok": False,
                    "error": "HTTP 500",
                },
            ]
            jsonl_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                encoding="utf-8",
            )

            policy_extract.flatten_to_csv(jsonl_path, items_csv, summary_csv)

            with items_csv.open(encoding="utf-8-sig", newline="") as f:
                item_rows = list(csv.DictReader(f))
            with summary_csv.open(encoding="utf-8-sig", newline="") as f:
                summary_rows = list(csv.DictReader(f))

        self.assertEqual(
            item_rows,
            [
                {
                    "source_file": "a.txt",
                    "chunk_index": "0",
                    "ability": "海洋生态评估与修复能力",
                    "evidence": "开展海洋生态环境整治修复技术研究",
                }
            ],
        )
        self.assertEqual(summary_rows[0]["source_file"], "a.txt")
        self.assertEqual(summary_rows[0]["items"], "1")
        self.assertEqual(summary_rows[1]["source_file"], "b.txt")
        self.assertEqual(summary_rows[1]["errors"], "1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail because the script does not exist**

Run:

```bash
python -m unittest tests.test_policy_competency_extraction -v
```

Expected: FAIL or ERROR with `FileNotFoundError` for `extract_policy_competencies_deepseek.py`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_policy_competency_extraction.py
git commit -m "test: add policy competency extraction tests"
```

## Task 2: Implement Pure Helpers And Prompt Constants

**Files:**
- Create: `extract_policy_competencies_deepseek.py`
- Test: `tests/test_policy_competency_extraction.py`

- [ ] **Step 1: Create `extract_policy_competencies_deepseek.py` with imports, prompt, and helper functions**

Create `extract_policy_competencies_deepseek.py` with this content:

```python
#!/usr/bin/env python3
from __future__ import annotations

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


SYSTEM_PROMPT = """你是海洋人才政策端能力推断专家。
你的任务是从海洋政策文本中抽取政策端隐含人才能力，用于与招聘需求端、高校供给端分别比较。

政策文本通常不会直接写“需要某某能力的人才”。你需要先识别政策中的具体任务、项目、平台、规划、工程、治理行动、产业方向、技术攻关、标准建设、监测体系、示范区建设等，再推断实施这些政策任务需要哪些中观能力人才。

只输出合法 JSON object，格式必须严格如下：
{
  "items": [
    {
      "ability": "能力短语",
      "evidence": "政策原文证据"
    }
  ]
}

字段要求：
1. ability：由政策任务推断出的中观能力单元，必须是中文短语，尽量 6-18 个汉字，优先以“能力”结尾。
2. evidence：必须摘取或紧贴政策原文，不要编造；应能支撑该能力推断，尽量 20-120 个汉字。
3. 每条 item 只能包含 ability 和 evidence 两个字段。不要输出 policy_task、inference、confidence、类别、解释、规范技能映射或其他字段。

推断规则：
1. 看到“建设、推进、实施、开展、完善、加强、打造、培育、发展、提升、构建、布局、攻关、示范、试点、监测、评估、修复、规划、管理、监管、标准、平台、工程、项目、产业链、创新中心、重点实验室”等政策任务词时，判断其隐含的人才能力。
2. 能力应体现海洋产业、海洋治理或涉海支撑场景，例如海洋生态、海洋环境、海洋信息、智慧港口、船舶海工、港航物流、海洋能源、水产渔业、海洋装备、海洋调查观测、海事监管等。
3. 不要把政策动词本身写成能力，例如不要输出“推进能力、建设能力、加强能力、落实能力、协调能力、宣传能力”。
4. 如果政策只包含宏观口号、原则表述、会议报道、成效宣传，且没有具体任务、项目、技术领域或治理场景，返回空 items。

颗粒度要求：
1. 使用中观尺度，与招聘需求端和高校供给端能力口径保持一致。
2. 不要过细到单个行政动作、材料报送、会议组织、资金拨付、通知印发。
3. 不要过泛到“管理能力、创新能力、服务能力、人才培养能力、政策研究能力”，除非带有明确涉海领域限定。
4. 合适示例：
   - “开展海洋生态环境整治修复技术研究” -> “海洋生态评估与修复能力”
   - “建设智慧港口和航运服务平台” -> “智慧港口建设运营能力”
   - “推进海上风电规模化开发” -> “海洋能源与海上风电工程能力”
   - “完善海洋环境监测预警体系” -> “海洋环境监测评价治理能力”
   - “发展海洋工程装备制造产业链” -> “海洋工程装备设计制造能力”

去噪规则：
1. 不抽取文件名称、发布日期、机关名称、索引号、字号、有效性、打印按钮、网页导航等 OCR 或网页噪声。
2. 不抽取纯政策流程、行政审批、资金安排、任务分工、宣传报道、会议召开、组织保障。
3. 不抽取“责任心、团队合作、沟通协调、国际视野”等泛化素质，除非它们是具体海洋国际合作或跨境航运业务能力的一部分。
4. 每个 chunk 最多返回 30 条 items；宁可少抽，不要用弱证据臆造能力。
5. 不要使用 Markdown，不要输出 JSON 以外的任何文字。
"""


HEADER_PREFIXES = (
    "源文件:",
    "提取状态:",
    "OCR引擎:",
    "OCR渲染比例:",
    "页数:",
    "平均置信度:",
)


def normalize_text(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def clean_policy_text(text: str) -> str:
    lines = normalize_text(text).splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in HEADER_PREFIXES):
            continue
        cleaned.append(stripped)
    return normalize_text("\n".join(cleaned))


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    text = normalize_text(text)
    if len(text) <= max_chars:
        return [text] if text else []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind("--- 第 "), window.rfind("。"))
            if cut > max_chars * 0.6:
                end = start + cut + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(0, end - overlap_chars)
    return chunks


def safe_json_loads(content: str) -> dict:
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


def normalize_items(parsed: dict) -> list[dict[str, str]]:
    raw_items = parsed.get("items") or parsed.get("competencies") or []
    items = []
    seen = set()
    for item in raw_items:
        ability = normalize_text(item.get("ability", ""))
        evidence = normalize_text(item.get("evidence", ""))
        if not ability or not evidence:
            continue
        key = (ability, evidence)
        if key in seen:
            continue
        seen.add(key)
        items.append({"ability": ability, "evidence": evidence})
    return items
```

- [ ] **Step 2: Run the tests and verify helper tests still fail only on missing `flatten_to_csv`**

Run:

```bash
python -m unittest tests.test_policy_competency_extraction -v
```

Expected: helper tests pass until `test_flatten_to_csv_writes_item_and_file_summary`, which fails with `AttributeError: module 'policy_extract' has no attribute 'flatten_to_csv'`.

## Task 3: Implement CSV Flattening And CLI-Free Data Helpers

**Files:**
- Modify: `extract_policy_competencies_deepseek.py`
- Test: `tests/test_policy_competency_extraction.py`

- [ ] **Step 1: Append chunk bookkeeping helpers and CSV flattening**

Append this code to `extract_policy_competencies_deepseek.py`:

```python
def append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_done_chunks(jsonl_path: Path) -> set[tuple[str, int]]:
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
                done.add((row.get("source_file", ""), int(row.get("chunk_index", 0))))
    return done


def flatten_to_csv(jsonl_path: Path, items_csv_path: Path, summary_csv_path: Path) -> None:
    item_rows = []
    summary: dict[str, dict[str, int]] = {}
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            source_file = row.get("source_file", "")
            chunk_index = int(row.get("chunk_index", 0))
            summary.setdefault(source_file, {"chunks": 0, "items": 0, "errors": 0})
            if not row.get("ok"):
                summary[source_file]["errors"] += 1
                continue
            summary[source_file]["chunks"] += 1
            items = normalize_items(row.get("parsed") or {})
            summary[source_file]["items"] += len(items)
            for item in items:
                item_rows.append(
                    {
                        "source_file": source_file,
                        "chunk_index": chunk_index,
                        "ability": item["ability"],
                        "evidence": item["evidence"],
                    }
                )

    with items_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["source_file", "chunk_index", "ability", "evidence"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(item_rows)

    with summary_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["source_file", "chunks", "items", "errors"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for source_file, stats in sorted(summary.items()):
            writer.writerow({"source_file": source_file, **stats})
```

- [ ] **Step 2: Run helper tests and verify they pass**

Run:

```bash
python -m unittest tests.test_policy_competency_extraction -v
```

Expected: all 5 tests pass.

- [ ] **Step 3: Commit helper implementation**

```bash
git add extract_policy_competencies_deepseek.py tests/test_policy_competency_extraction.py
git commit -m "feat: add policy extraction helpers"
```

## Task 4: Implement DeepSeek API Call And CLI Orchestration

**Files:**
- Modify: `extract_policy_competencies_deepseek.py`

- [ ] **Step 1: Append argument parsing, task creation, DeepSeek call, and `main`**

Append this code to `extract_policy_competencies_deepseek.py`:

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Infer policy-side marine talent competencies from OCR policy texts with DeepSeek."
    )
    parser.add_argument("--input-dir", default="海洋人才政策（删减后）_OCR文本/海洋人才政策")
    parser.add_argument("--output-dir", default="政策端_DeepSeek能力推断_海洋人才政策")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--chunk-chars", type=int, default=60000)
    parser.add_argument("--overlap-chars", type=int, default=2000)
    parser.add_argument("--max-output-tokens", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N files.")
    parser.add_argument("--force", action="store_true", help="Re-run chunks already present in output JSONL.")
    parser.add_argument("--no-thinking", action="store_true", default=True)
    return parser.parse_args()


def build_tasks(input_dir: Path, limit: int, chunk_chars: int, overlap_chars: int) -> list[dict]:
    files = sorted(input_dir.rglob("*.txt"))
    if limit:
        files = files[:limit]
    tasks = []
    for path in files:
        rel = str(path.relative_to(input_dir))
        text = clean_policy_text(read_text(path))
        chunks = split_text(text, chunk_chars, overlap_chars)
        for chunk_index, chunk in enumerate(chunks):
            tasks.append(
                {
                    "source_file": rel,
                    "chunk_index": chunk_index,
                    "chunk_count": len(chunks),
                    "char_start_hint": max(0, chunk_index * (chunk_chars - overlap_chars)),
                    "text": chunk,
                }
            )
    return tasks


def call_deepseek(
    api_key: str,
    base_url: str,
    model: str,
    task: dict,
    max_tokens: int,
    no_thinking: bool,
) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    user_prompt = f"""请从以下海洋政策文本 chunk 中推断政策端人才能力。
只返回 JSON object，items 中每条 item 只能有 ability 和 evidence 两个字段。

文件名：{task["source_file"]}
chunk：{task["chunk_index"] + 1}/{task["chunk_count"]}

文本：
<<<
{task["text"]}
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
            parsed = safe_json_loads(message.get("content") or "")
            return {"ok": True, "parsed": {"items": normalize_items(parsed)}, "usage": payload.get("usage", {})}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {exc.code}: {detail[:1000]}"
            if exc.code in (400, 401, 403):
                break
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(min(2**attempt, 20))
    return {"ok": False, "error": last_error}


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("Missing DEEPSEEK_API_KEY in environment.", file=sys.stderr)
        return 2

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "policy_competency_chunks.jsonl"
    items_csv_path = output_dir / "policy_competency_items.csv"
    summary_csv_path = output_dir / "policy_competency_file_summary.csv"

    tasks = build_tasks(input_dir, args.limit, args.chunk_chars, args.overlap_chars)
    done = set() if args.force else load_done_chunks(jsonl_path)
    tasks = [task for task in tasks if (task["source_file"], task["chunk_index"]) not in done]
    print(f"Pending chunks: {len(tasks)} | output: {output_dir}", flush=True)

    def run_task(task: dict) -> dict:
        result = call_deepseek(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            task=task,
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
            print(
                f"[{completed}/{len(tasks)}] {status} {row['source_file']} chunk {row['chunk_index'] + 1}/{row['chunk_count']}",
                flush=True,
            )

    if jsonl_path.exists():
        flatten_to_csv(jsonl_path, items_csv_path, summary_csv_path)
        print(f"Wrote: {jsonl_path}")
        print(f"Wrote: {items_csv_path}")
        print(f"Wrote: {summary_csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run unit tests**

Run:

```bash
python -m unittest tests.test_policy_competency_extraction -v
```

Expected: all 5 tests pass.

- [ ] **Step 3: Verify missing API key path**

Run:

```bash
python extract_policy_competencies_deepseek.py --limit 1
```

Expected: exit code `2` and stderr contains `Missing DEEPSEEK_API_KEY in environment.`

- [ ] **Step 4: Commit CLI and API implementation**

```bash
git add extract_policy_competencies_deepseek.py
git commit -m "feat: add policy competency DeepSeek extraction CLI"
```

## Task 5: Smoke Test With DeepSeek And Review Output Shape

**Files:**
- Runtime output: `政策端_DeepSeek能力推断_海洋人才政策/`

- [ ] **Step 1: Confirm the API key is available**

Run:

```bash
python -c "import os; raise SystemExit(0 if os.environ.get('DEEPSEEK_API_KEY') else 2)"
```

Expected: exit code `0`. If exit code is `2`, set `DEEPSEEK_API_KEY` in the shell before continuing.

- [ ] **Step 2: Run a small policy extraction sample**

Run:

```bash
python extract_policy_competencies_deepseek.py --limit 3 --workers 1 --chunk-chars 30000 --max-output-tokens 4000 --force
```

Expected:

```text
Pending chunks: <positive number> | output: 政策端_DeepSeek能力推断_海洋人才政策
[1/<N>] ok ...
Wrote: 政策端_DeepSeek能力推断_海洋人才政策\policy_competency_chunks.jsonl
Wrote: 政策端_DeepSeek能力推断_海洋人才政策\policy_competency_items.csv
Wrote: 政策端_DeepSeek能力推断_海洋人才政策\policy_competency_file_summary.csv
```

- [ ] **Step 3: Verify CSV fields and model item shape**

Run:

```powershell
@'
import csv, json
from pathlib import Path
out = Path('政策端_DeepSeek能力推断_海洋人才政策')
with (out / 'policy_competency_items.csv').open(encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    print(reader.fieldnames)
    rows = list(reader)
print('items', len(rows))
with (out / 'policy_competency_chunks.jsonl').open(encoding='utf-8') as f:
    first_ok = next(json.loads(line) for line in f if json.loads(line).get('ok'))
item_keys = sorted(first_ok['parsed']['items'][0].keys()) if first_ok['parsed']['items'] else []
print('item_keys', item_keys)
'@ | python -
```

Expected:

```text
['source_file', 'chunk_index', 'ability', 'evidence']
items <non-negative integer>
item_keys ['ability', 'evidence']
```

- [ ] **Step 4: Manually inspect the first 20 items**

Run:

```powershell
@'
import csv
from pathlib import Path
path = Path('政策端_DeepSeek能力推断_海洋人才政策') / 'policy_competency_items.csv'
with path.open(encoding='utf-8-sig', newline='') as f:
    for idx, row in enumerate(csv.DictReader(f), start=1):
        print(idx, row['ability'], '=>', row['evidence'][:120])
        if idx >= 20:
            break
'@ | python -
```

Expected: abilities are mid-level marine policy-side abilities and evidence is policy text, not OCR headers or generic slogans.

## Task 6: Full Run And Final Verification

**Files:**
- Runtime output: `政策端_DeepSeek能力推断_海洋人才政策/`

- [ ] **Step 1: Run the full extraction**

Run:

```bash
python extract_policy_competencies_deepseek.py --workers 2
```

Expected: script skips already successful chunks and writes the three output files.

- [ ] **Step 2: Verify summary counts**

Run:

```powershell
@'
import csv, json
from pathlib import Path
out = Path('政策端_DeepSeek能力推断_海洋人才政策')
chunks = [json.loads(line) for line in (out / 'policy_competency_chunks.jsonl').open(encoding='utf-8') if line.strip()]
ok = sum(1 for row in chunks if row.get('ok'))
err = sum(1 for row in chunks if not row.get('ok'))
with (out / 'policy_competency_items.csv').open(encoding='utf-8-sig', newline='') as f:
    items = list(csv.DictReader(f))
with (out / 'policy_competency_file_summary.csv').open(encoding='utf-8-sig', newline='') as f:
    summary = list(csv.DictReader(f))
print('chunks', len(chunks))
print('ok', ok)
print('errors', err)
print('items', len(items))
print('files', len(summary))
bad_keys = []
for row in chunks:
    if row.get('ok'):
        for item in (row.get('parsed') or {}).get('items') or []:
            if sorted(item.keys()) != ['ability', 'evidence']:
                bad_keys.append(sorted(item.keys()))
print('bad_item_key_shapes', bad_keys[:5])
'@ | python -
```

Expected:

```text
errors 0
bad_item_key_shapes []
```

If `errors` is greater than `0`, rerun the full extraction once. The script skips successful chunks and retries only failed or missing chunks unless `--force` is used.

- [ ] **Step 3: Commit the completed extraction script and tests**

```bash
git add extract_policy_competencies_deepseek.py tests/test_policy_competency_extraction.py
git commit -m "feat: infer policy-side marine talent competencies"
```

Do not commit generated output files unless the user explicitly asks to version the extracted data.

## Self-Review Against Spec

- Independent policy-side dataset: covered by `--output-dir` default and no changes to supply or demand scripts.
- Model output only `ability` and `evidence`: covered by `SYSTEM_PROMPT`, `normalize_items`, and verification of item keys.
- Reads OCR policy text: covered by `--input-dir` default and `build_tasks`.
- Removes extraction headers: covered by `clean_policy_text` and unit test.
- Long text chunking: covered by `split_text` and unit test.
- Restartable JSONL and flattened CSV: covered by `append_jsonl`, `load_done_chunks`, `flatten_to_csv`, and full-run verification.
- Small validation run before full extraction: covered by Task 5.
