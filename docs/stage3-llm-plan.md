# Stage 3 preparation: LLM candidates and cost estimates for the note grid

Date: 2026-10-27. Research and estimates only: no money was spent and no models were downloaded before the decision.

> **What was actually run (same day)**: Qwen3.8-27B as the mid tier and gpt-oss-120b as the large tier; the grid uses the mixed channel only. Differences from this plan:
> - The mid tier did not run on the local 5080 but on a rented A100 together with the large tier, quantised as Q4_K_M like the 14B.
> - The 14B was regenerated on the A100 as well.
> - gpt-oss-120b ran as Ollama's MXFP4 on a second A100, because the first server's disk could not hold it.
>
> Results: `docs/stage3-grid-results.md`.

## 0. Assumptions

- **Grid**: rows are transcript sources, columns are the LLMs that write the notes. Each cell is 25 consultations drawn from the 47 test consultations.
  - The estimates assume 5 rows per column: human transcript, Whisper separated / mixed, Qwen3-ASR separated / mixed.
  - That is 125 notes per LLM.
- **Kept fixed**: generation settings as for the current Qwen3 14B (temperature 0, fixed seed, thinking off, prompt v3); judging with the frozen judge v1.
- **Measured usage per note** (Qwen3 14B, test47):
  - Input: human transcript 2,386 tokens on average, at most 3,561; ASR sources 1,700–2,000.
  - Output: about 340 tokens.
  - The context never exceeds about 4,000 tokens, so VRAM goes mostly to the weights; the KV cache is small.

## 1. Mid tier (about 30B) candidates

Model names, parameter counts and licences checked on the Hugging Face model pages; BF16 weight sizes are the actual file sizes.

| Candidate | Released | Parameters | Licence | BF16 weights | Reason |
|---|---|---|---|---|---|
| **Qwen3.8-27B** (`Qwen/Qwen3.8-27B`) | 2026-08 | 27.8B, dense | Apache 2.0 | 55.6 GB | Highest overall ranking of these mid-tier models (16th on the BenchLM open-weight board, 59.7; GPQA Diamond 89.2, aggregator data). Same family as the current Qwen3 14B, which keeps the model axis cleaner. An official FP8 version also exists |
| **Gemma 4 31B-it** (`google/gemma-4-31B-it`) | 2026-03 | 31.3B, dense | Apache 2.0 | 62.5 GB | Most mature, best tooling support, most downloads. A different family, useful as a robustness check: does the conclusion hold beyond Qwen? |
| Muse Glimmer 30B (`meta-models/Muse-Glimmer-30B`) | 2026-08 | 29.6B, dense | Apache 2.0 | about 59 GB | Meta's newest open mid-size model. Meta says it beats Gemma 4 31B on 19 of 24 benchmarks, not independently verified; released only two months ago and inference-framework support is still immature |

**Medical models (optional controls only)**: MedGemma 27B text (2025, HAI-DEF licence, access on request) and Baichuan-M2-32B (2025, Apache 2.0). Their base models are a generation older than the three above and lag in general ability. A column for them would answer "does medical fine-tuning help?", but they are not recommended for the main line.

**Recommendation: Qwen3.8-27B as the mid tier.**

## 2. Large tier (about 70B) candidates on a single 80 GB GPU

There is no new mainstream dense 70B model in 2026. Today's "large tier" is mostly about-120B MoE models that fit in 80 GB only with 4-bit weights.

| Candidate | Released | Parameters | Licence | How it runs on 80 GB | Reasons and risks |
|---|---|---|---|---|---|
| **gpt-oss-120b** (`openai/gpt-oss-120b`) | 2025-08 | 117B MoE, 5.1B active | Apache 2.0 | Native MXFP4, about 61–63 GB, fits on one GPU | The only large model designed natively for a single 80 GB GPU; few active parameters, so fast. It is a reasoning model: set reasoning effort to low and record the reasoning tokens. **That it runs on A100 is a third-party report** (vLLM / llama.cpp; TensorRT-LLM does not work on A100); verify for 15 minutes after renting |
| **Llama 3.3 70B Instruct** (`meta-llama/Llama-3.3-70B-Instruct`) | 2024-12 | 70.6B, dense | Llama 3.3 (access on request) | AWQ INT4 about 40 GB, or 8-bit about 71 GB (tight) | The only mainstream dense 70B and the most common in the literature, which helps comparison with other work. Oldest of the three; overall weaker than a 2026 27B |
| Qwen3.5-122B-A10B (`Qwen/Qwen3.5-122B-A10B`) | 2026-02 | 125B MoE, 10B active | Apache 2.0 | The official GPTQ-Int4 is 78.9 GB, **does not fit on one 80 GB GPU** (KV cache needs room too) | The best-quality large option, and with Qwen3.5-27B it forms a same-generation size ladder. Costs two A100s or one 141 GB H200, doubling the price |

**Recommendation: gpt-oss-120b as the large tier, Llama 3.3 70B as the fallback.** If a same-family size ladder matters more, use Qwen3.5 27B and 122B instead and rent two GPUs.

**Design caveat:** by overall ranking, the 2026 Qwen3.8-27B (59.7) is above gpt-oss-120b (37.4) and Qwen3.5-122B (41.8). So "mid vs large" mixes in "new generation vs old", and cannot be read as a model-size effect. Two ways to handle it:

- call this axis "available model tiers" rather than "model size" in the report;
- or use a same-generation ladder (Qwen3.5: 9B / 27B / 122B-A10B).

## 3. Can the 16 GB 5080 run the mid tier?

| Quantisation (Qwen3.8-27B GGUF, unsloth) | Weights | Fits in 16 GB? |
|---|---|---|
| Q4_K_M | 16.5 GB | No; part must go to system RAM (31 GB here), 3–5× slower |
| IQ4_XS | 14.3 GB | Just. About 1.5 GB left for KV cache and CUDA; our context stays under about 4,500 tokens, which should fit, to be tested |
| Q3_K_XL | 13.1 GB | Comfortably, but more quantisation loss |

- **Gemma 4 31B**: 4-bit is about 18–19 GB and must partly go to system RAM; 3-bit is about 13–14 GB.
- **Large tier**: impossible on the 5080. Even a 2-bit 120B needs more than 40 GB.

**Conclusion:** the mid tier can run locally for free as IQ4_XS, at an estimated 30–40 tokens per second, 12–15 s per note, about 6 minutes per 25-consultation cell.

The condition is that every cell in a column uses the same weights: either the whole mid-tier column runs locally at 4 bits, or all of it runs on a rented GPU in BF16, never mixed. 4-bit usually costs one or two benchmark points relative to BF16, but this has not been checked on our task.

## 4. Rental time and cost (A100 80 GB)

**Time per note** (single stream, greedy decoding, estimated from 2.0 TB/s memory bandwidth):

| Tier | Per note | Per 25-consultation cell |
|---|---|---|
| Mid tier BF16 (about 56–63 GB weights) | about 15 s | about 6–7 min |
| gpt-oss-120b (5.1B active, plus low-effort reasoning tokens) | about 12–17 s | about 7 min |
| Llama 3.3 70B AWQ INT4 | about 14 s | about 6 min |

**Fixed overhead per rental**, about 0.7–1 hour per model: start the machine, install vLLM, download 60–70 GB of weights, load the model, and generate 3–5 trial notes. This takes longer than the generation itself.

| Option | Estimated time (with 50% margin) | Vast.ai ($0.5–1.5/h) | RunPod ($1.2–1.8/h) | Lambda ($2.0–2.8/h) |
|---|---|---|---|---|
| Each additional cell (25 consultations) | about 0.12 h | $0.06–0.18 | $0.15–0.22 | $0.24–0.34 |
| Mid and large tier both rented, 5 cells each | about 4–5 h | $2–8 | $5–9 | $8–14 |
| Mid tier local, large tier rented | about 2–2.5 h | $1–4 | $2.5–4.5 | $4–7 |
| Large tier as Qwen3.5-122B (two A100s) | about 2.5 h × 2 GPUs | $2.5–7.5 | $6–9 | $10–14 |

- Disk for the weights costs very little (about 200 GB for a day, under $1).
- Suggested budget cap **$20**; run both models in the same rental to pay the fixed overhead once.
- Prices are public quotes from August–October 2026 and vary a lot; check the day's price before renting.
- Vast.ai is cheapest but machine quality varies and runs can drop. RunPod is the middle ground.

## 5. Claude judging quota

**One measured judge call** (Opus 5.5, frozen judge v1, a note with 30 facts):

| Item | Value |
|---|---|
| Input | about 2,800 tokens (written to cache on first use) |
| Output | about 1,800 tokens (530 of them thinking) |
| Time | about 15 s |
| At API list price | $0.058 |

This runs on a personal subscription and is not billed at this price; the figure is only for comparing with earlier usage.

**Calls needed for the grid:**

| Item | Calls |
|---|---|
| Two new LLMs × 5 rows × 25 consultations | 250 |
| Two Qwen3-ASR rows × the existing local 14B column × 25 consultations (the 14B column's other rows can reuse the test47 judgements) | 50 |
| About 10% judged again, to measure the judge's own noise | 30 |
| **Total** | **about 330** |

- **Fact lists**: the 25 consultations all come from the 47 test consultations, whose fact lists are already cached; no new calls are needed.
- **Volume**: about 0.9M input and 0.6M output tokens; about $19 at list price; about 80 minutes run one after another.
- **Compared with before**: the test-set round made about 470 calls on the same subscription (376 judgements, 47 fact splits, 47 stated-fact checks) without hitting the usage limit; only one server overload (529), which succeeded on retry. This is about 70% of that round.
- **The subscription's exact limits are not visible.** If a limit is hit, the judge script resumes; it can be finished across two sessions.

## 6. Decisions needed

1. Which mid tier: Qwen3.8-27B (recommended), Gemma 4 31B, or both.
2. Mid tier locally at 4 bits (free), or rented in BF16.
3. Large tier: gpt-oss-120b (recommended), Llama 3.3 70B, or Qwen3.5-122B on two rented GPUs.
4. Grid rows: the 5 assumed above or not; and how to get word times for Qwen3-ASR separated-channel notes: forced alignment, or interleaving by chunk (see section 4 of `results/test47/asr_selection.md`).
5. Which provider, and the budget cap.

## Sources

- Model parameters, licences and weight sizes: Hugging Face model pages and API, queried 2026-10-27.
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
