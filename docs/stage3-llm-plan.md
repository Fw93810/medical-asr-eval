# 第三阶段准备：病历网格的 LLM 候选与费用估算

日期：2026-10-27。这份文档只做调研和估算，没有花钱，也没有下载模型，等决定后再开始。

## 0. 前提

- **网格**：行是转写来源，列是生成病历的 LLM。每格是 25 段问诊，从测试集 47 段里抽出。
  - 估算时假设每列 5 行：人工转写，Whisper 分声道 / 合并，Qwen3-ASR 分声道 / 合并。
  - 也就是每个 LLM 生成 125 份病历。
- **固定不变的部分**：生成设置和现在的 Qwen3 14B 一样（温度 0、固定种子、关闭思考、提示词 v3）；评判用冻结的 judge v1。
- **实测的每份病历用量**（Qwen3 14B，test47）：
  - 输入：人工转写平均 2,386 个 token，最多 3,561；ASR 来源 1,700–2,000。
  - 输出：约 340 个 token。
  - 上下文不超过约 4,000 token，所以显存主要花在模型权重上，KV 缓存很小。

## 1. 中档（约 30B）候选

模型名、参数量和许可证都从 Hugging Face 模型页核对过，BF16 权重大小按文件实际大小计。

| 候选 | 发布 | 参数 | 许可证 | BF16 权重 | 理由 |
|---|---|---|---|---|---|
| **Qwen3.8-27B**（`Qwen/Qwen3.8-27B`） | 2026-08 | 27.8B，稠密 | Apache 2.0 | 55.6 GB | 综合排名在这几个中档模型里最高（BenchLM 开源榜第 16，59.7 分；GPQA Diamond 89.2，聚合站数据）。和现在用的 Qwen3 14B 同一家族，"模型大小"这条轴更干净。官方另有 FP8 版本 |
| **Gemma 4 31B-it**（`google/gemma-4-31B-it`） | 2026-03 | 31.3B，稠密 | Apache 2.0 | 62.5 GB | 最成熟，工具链支持最好，下载量最大。家族不同，可以作稳健性检查：看结论是不是只对 Qwen 成立 |
| Muse Glimmer 30B（`meta-models/Muse-Glimmer-30B`） | 2026-08 | 29.6B，稠密 | Apache 2.0 | 约 59 GB | Meta 最新的开源中档模型。Meta 称它在 24 项里有 19 项胜过 Gemma 4 31B，但没有独立验证；发布才两个多月，推理框架支持还不成熟 |

**医疗专用模型（只作可选对照）**：MedGemma 27B text（2025，HAI-DEF 许可，需申请）和 Baichuan-M2-32B（2025，Apache 2.0）。它们的底座比上面三个旧一代，通用能力已经落后。如果想回答"医疗微调有没有用"，可以加一列，但不建议当主线。

**推荐 Qwen3.8-27B 作为中档。**

## 2. 大档（约 70B）候选：单张 80 GB

2026 年没有新的稠密 70B 主流模型。现在的"大档"基本是约 120B 的 MoE 模型，用 4 位权重才能放进 80 GB。

| 候选 | 发布 | 参数 | 许可证 | 80 GB 上的跑法 | 理由与风险 |
|---|---|---|---|---|---|
| **gpt-oss-120b**（`openai/gpt-oss-120b`） | 2025-08 | 117B MoE，激活 5.1B | Apache 2.0 | 原生 MXFP4，约 61–63 GB，单卡放得下 | 唯一原生为单张 80 GB 设计的大模型，激活参数少，所以快。它是推理模型，要把推理强度设成 low，并记下推理 token 数。**A100 能跑是第三方报告的**（vLLM / llama.cpp；TensorRT-LLM 在 A100 上不行），租到后先花 15 分钟验证 |
| **Llama 3.3 70B Instruct**（`meta-llama/Llama-3.3-70B-Instruct`） | 2024-12 | 70.6B，稠密 | Llama 3.3（需申请） | AWQ INT4 约 40 GB，或 8 位约 71 GB（偏紧） | 唯一主流的稠密 70B，文献里最常见，便于和别人的结果对比。缺点是年头最旧，综合能力不如 2026 年的 27B |
| Qwen3.5-122B-A10B（`Qwen/Qwen3.5-122B-A10B`） | 2026-02 | 125B MoE，激活 10B | Apache 2.0 | 官方 GPTQ-Int4 有 78.9 GB，**单张 80 GB 放不下**（还要留 KV 缓存） | 质量最好的大档选项，而且和 Qwen3.5-27B 能组成同一代的大小阶梯。代价是要两张 A100，或一张 141 GB 的 H200，费用翻倍 |

**推荐 gpt-oss-120b 作为大档，Llama 3.3 70B 作为备选。** 如果更看重"同一家族的大小阶梯"，就改用 Qwen3.5 的 27B 和 122B，接受租两张卡。

**设计上要注意：** 按综合排名，2026 年的 Qwen3.8-27B（59.7 分）高于 gpt-oss-120b（37.4）和 Qwen3.5-122B（41.8）。所以"中档对大档"的差异里混着"新一代对旧一代"，不能直接解释成模型大小的效应。有两种处理办法：

- 在报告里把这一轴叫作"可用模型档位"，不叫"模型大小"；
- 或者用同一代的大小阶梯（Qwen3.5：9B / 27B / 122B-A10B）。

## 3. 16 GB 的 5080 能不能跑中档

| 量化（Qwen3.8-27B GGUF，unsloth） | 权重 | 放进 16 GB？ |
|---|---|---|
| Q4_K_M | 16.5 GB | 放不下，要部分放到内存（本机内存 31 GB），速度会慢 3–5 倍 |
| IQ4_XS | 14.3 GB | 刚好。剩约 1.5 GB 给 KV 缓存和 CUDA；我们的上下文不超过约 4,500 token，应该够，要实测 |
| Q3_K_XL | 13.1 GB | 宽松，但量化损失更大 |

- **Gemma 4 31B**：4 位约 18–19 GB，必须部分放到内存；3 位约 13–14 GB。
- **大档**：5080 上不可能。2 位的 120B 也要 40 GB 以上。

**结论：** 中档可以在本机用 IQ4_XS 免费跑。估计每秒 30–40 个 token，每份病历 12–15 秒，每格 25 段约 6 分钟。

条件是同一列里所有格子必须用同一份权重。也就是说，要么整个中档列都用本机 4 位，要么全部租卡用 BF16，不能混用。4 位相对 BF16 的质量损失一般在基准分数上只有一两个百分点，但没有在我们的任务上验证过。

## 4. 租卡时间和费用（A100 80 GB）

**单份病历的时间**（单路、贪心解码，按显存带宽 2.0 TB/s 估算）：

| 档位 | 每份病历 | 每格 25 段 |
|---|---|---|
| 中档 BF16（约 56–63 GB 权重） | 约 15 秒 | 约 6–7 分钟 |
| gpt-oss-120b（激活 5.1B，加上 low 强度的推理 token） | 约 12–17 秒 | 约 7 分钟 |
| Llama 3.3 70B AWQ INT4 | 约 14 秒 | 约 6 分钟 |

**每租一次的固定开销**，每个模型约 0.7–1 小时：开机、装 vLLM、下载 60–70 GB 权重、加载模型、先生成 3–5 份试跑检查。这部分比真正生成的时间还长。

| 方案 | 估计时长（含 50% 余量） | Vast.ai（$0.5–1.5/时） | RunPod（$1.2–1.8/时） | Lambda（$2.0–2.8/时） |
|---|---|---|---|---|
| 每增加一格（25 段） | 约 0.12 小时 | $0.06–0.18 | $0.15–0.22 | $0.24–0.34 |
| 中档 + 大档都租，各 5 格 | 约 4–5 小时 | $2–8 | $5–9 | $8–14 |
| 中档在本机跑，只租大档 | 约 2–2.5 小时 | $1–4 | $2.5–4.5 | $4–7 |
| 大档换成 Qwen3.5-122B（两张 A100） | 约 2.5 小时 × 2 张卡 | $2.5–7.5 | $6–9 | $10–14 |

- 磁盘存放权重的费用很少（约 200 GB 放一天，不到 $1）。
- 建议预算上限 **$20**，而且两个模型放在同一次租用里连续跑，省一次固定开销。
- 价格是 2026 年 8–10 月的公开报价，各家变动很大，租之前要看当天价格。
- Vast.ai 最便宜，但机器质量参差，可能中途断。RunPod 是折中。

## 5. Claude 评判的额度

**实测一次评判调用**（Opus 5.5，冻结的 judge v1，一份 30 条事实的病历）：

| 项目 | 数值 |
|---|---|
| 输入 | 约 2,800 token（首次写入缓存） |
| 输出 | 约 1,800 token（其中思考 530） |
| 耗时 | 约 15 秒 |
| 按 API 标价折算 | $0.058 |

用的是你的订阅，不按这个价格收钱。这个数只用来和以前的用量比较。

**网格要多少次调用：**

| 项目 | 调用次数 |
|---|---|
| 两个新 LLM × 5 行 × 25 段 | 250 |
| Qwen3-ASR 两行 × 现有的本地 14B 列 × 25 段（14B 列的其他行可以直接复用 test47 已有的评判） | 50 |
| 约 10% 重评，测评判自身的噪声 | 30 |
| **合计** | **约 330** |

- **事实清单**：25 段都从测试集 47 段里抽，每段的事实清单已经缓存过，不需要再调用。
- **总量**：约 0.9M 输入、0.6M 输出 token；按标价折算约 $19；顺序跑约 80 分钟。
- **和以前比**：测试集那一轮在同一个订阅上一共调用了约 470 次（376 次评判、47 次拆事实、47 次查事实是否说过），没有碰到用量上限，只有一次服务器过载（529）后重试成功。这次约为那一轮的 70%。
- **我看不到订阅的具体上限。** 如果中途碰到上限，评判脚本可以续跑，分两个时段跑完就行。

## 6. 需要你决定的事

1. 中档用哪个：Qwen3.8-27B（推荐）、Gemma 4 31B，还是两个都要。
2. 中档在本机跑 4 位（免费），还是租卡跑 BF16。
3. 大档用 gpt-oss-120b（推荐）、Llama 3.3 70B，还是租两张卡跑 Qwen3.5-122B。
4. 网格的行：是否就是上面假设的 5 行。还有 Qwen3-ASR 分声道病历需要的词级时间：用强制对齐补，还是按段交织（见 `results/test47/asr_selection.md` 第 4 节）。
5. 在哪家租卡，预算上限多少。

## 来源

- 模型参数、许可证、权重大小：Hugging Face 模型页和 API，2026-10-27 查询。
- [Open Source LLM Comparison Table (2026)](https://computingforgeeks.com/open-source-llm-comparison/)
- [Open-Source LLM Leaderboard 2026 (BenchLM)](https://benchlm.ai/best/open-source)
- [Qwen3.8-27B vs Muse Glimmer-30B (DataLearner)](https://www.datalearner.com/en/ai-models/compare/qwen3-8-27b/vs/muse-glimmer-30b)
- [Muse Glimmer-30B vs Gemma 4 31B (DataLearner)](https://www.datalearner.com/en/ai-models/compare/muse-glimmer-30b/vs/google-gemma-4-31b)
- [Muse Glimmer explained](https://www.orcarouter.ai/blog/muse-glimmer-explained)
- [Best Open-Source LLMs to Self-Host in 2026: VRAM Tier Guide (Spheron)](https://www.spheron.network/blog/best-open-source-llms-self-host-2026-vram-guide/)
- [vLLM Now Supports gpt-oss](https://vllm.ai/blog/2025-08-05-gpt-oss)
- [gpt-oss-120b on A100 80GB with llama.cpp (Markaicode)](https://markaicode.com/benchmarks/llamacpp-mixtral-a100-80gb-throughput-benchmark/)
- [How to run OpenAI gpt-oss with vLLM (Ori)](https://www.ori.co/blog/how-to-run-openai-gpt-oss-with-vllm)
- [GPU Cloud Pricing Comparison: Runpod vs Vast.ai (2026)](https://www.spheron.network/blog/gpu-cloud-pricing-comparison-runpod-vs-vastai-2026/)
- [RunPod vs Lambda vs Vast.ai: GPU Pricing 2026](https://tech-insider.org/runpod-vs-lambda-vs-vast-ai-2026/)
- [NVIDIA A100 Price in 2026 (Jarvislabs)](https://jarvislabs.ai/blog/a100-price)
