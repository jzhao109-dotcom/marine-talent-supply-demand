# Policy Competency Inference Design

## Goal

Extract an independent policy-side competency dataset from `海洋人才政策（删减后）_OCR文本`.

The policy-side dataset represents strategic talent demand implied by marine policy tasks, projects, platforms, plans, governance actions, and industrial development directions. It must remain separate from the existing recruitment demand dataset and the curriculum supply dataset.

## Scope

The workflow will call the DeepSeek API over OCR text files and produce policy-side competency items.

The output item schema is intentionally minimal:

```json
{
  "ability": "能力短语",
  "evidence": "政策原文证据"
}
```

No `policy_task`, `inference`, `confidence`, category, or canonical mapping field will be included in the item output.

## Extraction Logic

The model should internally infer abilities from policy tasks, but only return `ability` and `evidence`.

Policy texts often do not state talent abilities directly. The prompt will therefore instruct the model to:

1. Identify explicit policy tasks, including major projects, industrial actions, platform construction, ecological governance, infrastructure construction, technology innovation, standards, monitoring systems, and demonstration zones.
2. Infer what mid-level marine talent ability would be needed to implement those tasks.
3. Write the inferred ability as a concise Chinese ability phrase, preferably ending with `能力`.
4. Use `evidence` to quote or closely paraphrase the policy sentence that supports the inferred ability.

Example:

Policy text:

```text
开展海洋资源开发生态环境响应与效应、海洋生态环境整治修复技术、海洋生态环境空间规划与环境经济政策制度研究
```

Output:

```json
{
  "ability": "海洋生态评估与修复能力",
  "evidence": "开展海洋资源开发生态环境响应与效应、海洋生态环境整治修复技术、海洋生态环境空间规划与环境经济政策制度研究"
}
```

## Granularity

Use the same mid-level competency scale as the existing supply and demand extraction scripts.

Good policy-side abilities should describe a domain, technology module, governance module, engineering module, or compound professional capability. They should not be isolated administrative actions, slogans, general qualities, or overly broad words such as `管理能力` or `创新能力`.

Preferred examples:

- `海洋生态评估与修复能力`
- `海洋环境监测评价治理能力`
- `智慧港口建设运营能力`
- `海洋工程装备设计制造能力`
- `海洋信息智能数据能力`
- `港航物流与航运业务能力`
- `海洋能源与海上风电工程能力`

The extraction should be conservative. If a policy paragraph only contains general slogans without a concrete task, project, sector, or governance action, it should return no item.

## Data Flow

1. Read `.txt` files from `海洋人才政策（删减后）_OCR文本/海洋人才政策`.
2. Normalize text and remove extraction headers.
3. Split long files into overlapping chunks.
4. Call DeepSeek with a policy-specific system prompt.
5. Write raw chunk responses to JSONL for restartability.
6. Flatten successful items into CSV.
7. Write a per-file summary with chunk and item counts.

## Outputs

Output directory:

```text
政策端_DeepSeek能力推断_海洋人才政策/
```

Files:

```text
policy_competency_chunks.jsonl
policy_competency_items.csv
policy_competency_file_summary.csv
```

CSV item fields:

```text
source_file,chunk_index,ability,evidence
```

The item-level model output remains only `ability` and `evidence`; `source_file` and `chunk_index` are added by the script for traceability.

## Error Handling

The script will follow the existing DeepSeek extraction pattern:

- Require `DEEPSEEK_API_KEY`.
- Support `--limit` for test runs.
- Support `--force` for reruns.
- Skip successful chunks on restart.
- Retry transient API failures.
- Preserve failed chunk errors in JSONL.

## Validation

Initial validation should run with a small `--limit` before full extraction.

Manual review should check:

1. Abilities are inferred from concrete policy tasks, not from slogans.
2. Evidence comes from policy text and can support the inferred ability.
3. Abilities match the existing mid-level competency style.
4. The result remains independent from recruitment demand and curriculum supply outputs.
