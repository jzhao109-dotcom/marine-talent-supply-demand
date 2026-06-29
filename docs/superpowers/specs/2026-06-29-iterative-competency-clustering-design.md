# 迭代式能力聚类 Skill 设计

## 目标

创建一个可复用的 Codex skill，用于把供给端、需求端、政策端抽取出的海洋人才能力短语，逐轮归并为可分析的中观规范技能。

第一版先支持政策端数据：

```text
政策端_DeepSeek能力推断_海洋人才政策/policy_competency_items.csv
```

当前政策端规模约为 5196 条能力记录、4427 个唯一原始能力。目标不是一次性压缩到几十个，而是通过多轮读取、审核、合并和审计，逐步形成稳定的规范技能体系。

## 核心口径

使用“无向量聚类”的直接审核归并流程。

不使用 embedding、相似度检索或向量聚类。每轮由 Codex 或 DeepSeek 直接读取上一轮能力表，依据能力对象、行动方式、应用场景、证据支撑和研究口径判断是否合并。

每轮只允许有限压缩，避免从几千条原始能力直接跳到几十个粗标签。推荐政策端压缩路径为：

```text
4427 原始唯一能力
-> 2500-3000 微技能
-> 1000-1500 子类技能
-> 300-500 中观候选技能
-> 40-80 最终规范技能
```

## 非目标

- 不重新抽取政策文本中的能力。
- 不修改现有 DeepSeek 提取脚本。
- 不使用向量聚类。
- 不把政策端能力强行套入供需端 40 类词典。
- 不生成只有最终标签、无法追溯原始证据的结果。

## Skill 形态

采用“流程 + 工具”型 skill。

建议 skill 名称：

```text
iterative-competency-clustering
```

默认创建位置：

```text
$CODEX_HOME/skills
```

如果未设置 `CODEX_HOME`，则创建到：

```text
~/.codex/skills
```

skill 目录建议包含：

```text
iterative-competency-clustering/
  SKILL.md
  agents/openai.yaml
  scripts/iterative_competency_clustering.py
  references/competency-clustering-rules.md
```

`SKILL.md` 保持短而强约束，说明触发条件、阶段流程、审计原则和常见错误。详细归并口径放到 `references/competency-clustering-rules.md`，脚本负责机械性读写、分批、断点续跑和报告生成。

## 数据输入

第一版支持政策端输入：

```text
source_file,chunk_index,ability,evidence
```

后续扩展到供给端：

```text
ability,evidence
```

后续扩展到需求端：

```text
source_index,招聘岗位,occupation_name,ability,evidence
```

脚本内部统一为标准记录：

```text
record_id,side,source_ref,occupation_name,ability,evidence
```

其中：

- `record_id` 是稳定行号或哈希，用于跨轮追溯。
- `side` 取 `policy`、`supply`、`demand`。
- `source_ref` 保存政策文件、招聘来源或其他来源标识。
- `occupation_name` 在政策端和供给端可为空。
- `ability` 和 `evidence` 必须保留。

## 每轮输出

每轮输出单独目录，例如：

```text
政策端_能力迭代聚类/round_01/
政策端_能力迭代聚类/round_02/
```

每轮至少生成四个文件：

```text
round_items.csv
round_dictionary.csv
review_flags.csv
round_report.md
```

`round_items.csv` 保存原始记录到本轮簇的映射：

```text
record_id,side,source_ref,occupation_name,ability,evidence,cluster_id,cluster_label,merge_status,merge_reason,confidence
```

`round_dictionary.csv` 保存本轮技能簇：

```text
cluster_id,cluster_label,member_count,representative_abilities,representative_evidence,definition,merge_status,confidence
```

`review_flags.csv` 保存需要人工复核的项：

```text
flag_type,cluster_id,cluster_label,record_id,ability,evidence,reason
```

`round_report.md` 汇总：

- 输入记录数、唯一能力数、本轮簇数、压缩率。
- 高置信合并数量、暂定合并数量、待复核数量。
- 最大簇和异常大簇。
- 跨域合并风险。
- 下一轮建议目标数量。

## 迭代流程

### 阶段 0：输入审计

读取输入 CSV，检查字段、空值、重复记录和 evidence 缺失情况。若 `ability` 或 `evidence` 大量为空，停止并报告，不能继续聚类。

### 阶段 1：文本规范化和精确去重

仅做保守清洗：

- 去除首尾空白。
- 统一全角半角空格。
- 合并完全相同的能力短语。
- 保留所有 evidence 和来源，不丢弃重复来源。

该阶段可以不用模型。

### 阶段 2：分批审核归并

脚本按批次读取上一轮能力簇，调用模型判断哪些能力可以合并。模型只处理当前批次，不直接决定全局最终体系。

合并判断优先级：

1. 专业对象是否一致。
2. 核心行动是否一致或可上收。
3. 应用场景是否属于同一中观能力边界。
4. evidence 是否支持该合并。
5. 合并后标签是否仍具有分析价值。

### 阶段 3：跨批次标签审计

每轮分批后必须再审计同名、近名和边界重叠的簇。重点检查：

- 同一含义被不同名称拆开。
- 不同含义被同一名称误合。
- 标签过宽，如“管理能力”“创新能力”。
- 标签过细，如只对应一个具体设备、项目或政策动作。

### 阶段 4：人工复核闸口

每轮结束必须产出 `review_flags.csv`。如果低置信、跨域或证据不足项过多，不进入下一轮，先修订本轮合并结果。

### 阶段 5：下一轮继续缩减

下一轮读取上一轮 `round_dictionary.csv` 和 `round_items.csv`，继续归并簇，而不是回到原始 CSV 重新开始。每一轮都保留到原始 `record_id` 的映射。

## 停止条件

当满足以下条件时，可以停止迭代并形成最终规范技能：

- 最终簇数进入用户设定范围，政策端建议为 40-80。
- 每个规范技能有清晰定义和代表 evidence。
- 每个规范技能能追溯到原始能力和政策原文来源。
- 低置信合并占比处于可接受范围。
- 没有明显的跨域大杂烩簇。

## 可选对齐步骤

政策端最终规范技能形成后，可选地与已有供需端 40 类词典对齐：

```text
供需能力开放编码_中观边界强化口径_全量/canonical_competency_dictionary.csv
```

对齐只作为分析层，不覆盖政策端独立聚类结果。输出应区分：

- 政策端独有能力。
- 与供给端和需求端共有的能力。
- 政策强、供需弱的前瞻性能力。
- 供需强、政策弱的市场化能力。

## 脚本接口

脚本建议命令：

```powershell
python scripts/iterative_competency_clustering.py `
  --side policy `
  --input "政策端_DeepSeek能力推断_海洋人才政策/policy_competency_items.csv" `
  --output "政策端_能力迭代聚类" `
  --round 1 `
  --target-count 2800 `
  --workers 8 `
  --resume
```

关键参数：

- `--side`：`policy`、`supply` 或 `demand`。
- `--input`：输入 CSV。
- `--output`：输出根目录。
- `--round`：本轮编号。
- `--target-count`：本轮建议目标簇数。
- `--workers`：并发 worker 数。
- `--resume`：跳过已完成批次。
- `--dry-run`：只做输入审计和批次规划，不调用模型。
- `--model`：模型名称，默认可沿用 DeepSeek。

## 模型输出约束

模型每批只返回结构化 JSON，不返回散文说明。每个输出项至少包含：

```json
{
  "cluster_label": "海洋生态监测评价能力",
  "definition": "围绕海洋生态环境监测、评估、预警和治理效果评价形成的综合能力。",
  "member_ids": ["..."],
  "merge_reason": "专业对象均为海洋生态环境，核心行动均为监测、评价或治理支撑。",
  "confidence": "high"
}
```

模型不得删除无法归并的能力。无法合并的能力应作为单独簇输出，或标记为 `review`。

## 质量控制

skill 必须明确禁止以下行为：

- 一轮内把数千个能力直接压缩到几十个。
- 只看 ability，不看 evidence。
- 为了达到目标数量而强行合并。
- 丢失原始来源和证据。
- 把政策端结果直接套用供需端既有词典。
- 把通用词当作规范技能，如“创新能力”“管理能力”。

每轮至少做以下检查：

- 行数守恒：原始记录数在 `round_items.csv` 中不能减少。
- 追溯完整：每个最终簇能追溯到所有原始 `record_id`。
- 证据存在：每个簇至少有代表 evidence。
- 压缩合理：压缩率与目标轮次一致。
- 异常簇审计：过大簇、跨域簇、低置信簇进入 `review_flags.csv`。

## Skill 测试策略

按 writing-skills 的要求，skill 实现前需要先设计压力场景，用来验证没有 skill 时 Codex 容易犯的错误。

建议至少测试三个压力场景：

1. 用户要求“直接把 4000 多条压到 40 条”。期望 skill 阻止一次性过度压缩，并要求分轮输出。
2. 用户只提供 `ability`，没有 `evidence`。期望 skill 停止并要求补充证据或明确只能做低置信草案。
3. 用户要求政策端直接套用供需端 40 类。期望 skill 保留政策端独立聚类，再做可选对齐。

通过标准：

- 使用 skill 后，Codex 能提出逐轮流程。
- 使用 skill 后，Codex 不会丢失 evidence 和来源字段。
- 使用 skill 后，Codex 会生成审计文件和下一轮建议，而不是只给最终标签。

## 实施顺序

1. 编写并提交本设计文档。
2. 用户审核设计文档。
3. 编写 implementation plan。
4. 创建 skill 目录。
5. 先写压力场景或最小验证样例。
6. 初始化 skill。
7. 编写 `SKILL.md`、reference 和脚本。
8. 运行 skill 校验脚本和脚本单元测试。
9. 在政策端小样本上 dry-run 验证输出结构。

## 自检结论

本设计没有依赖向量聚类，没有要求重新抽取政策能力，也没有把政策端强制映射到既有供需词典。实现范围集中在一个新 skill 和一个可复用脚本上，首版从政策端开始，后续可扩展到供给端和需求端。
