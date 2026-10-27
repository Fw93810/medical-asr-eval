# 本地冒烟测试：环境与配置说明

记录时间：2026-10-26。这份文件说明这台电脑上冒烟测试的环境怎么搭、每一轮怎么跑、有哪些已知问题，方便以后复现或换机器。

## 1. 硬件与系统

| 项目 | 配置 |
|---|---|
| 显卡 | NVIDIA GeForce RTX 5080 Laptop，16 GB 显存，Blackwell 架构（sm_120） |
| 驱动 | 610.62（支持 CUDA 13.3） |
| 系统 | Windows 11 家庭中文版 |
| 系统级 CUDA Toolkit | 没有安装。CUDA 运行库都用 pip 装在各个虚拟环境里 |
| ffmpeg | 没有安装，也不需要（音频是 wav，PyAV 自带解码） |

## 2. 文件位置（全部在 D 盘）

| 路径 | 内容 |
|---|---|
| `D:\medical-asr-eval` | 仓库 |
| `D:\Python311` | Python 3.11.9（通过 winget 安装，没有加进系统 PATH，不影响原来的 Python 3.13） |
| `D:\cache\huggingface` | 模型缓存（`HF_HOME`） |
| `D:\cache\pip` | pip 缓存 |
| `data\primock57` | PriMock57 原始数据（57 段问诊全部下载） |
| `data\prepared_3min` | 前 3 段问诊，每段裁剪到前约 3 分钟 |
| `data\prepared_full10` | 前 10 段问诊，完整长度：**开发集**，用来选解码设置和定分析方法 |
| `data\prepared_test47` | 其余 47 段问诊，完整长度：**测试集**，最终数字只报这一组 |
| `D:\Tools\GitHubCLI` | GitHub CLI（`gh`），已登录 Fw93810 |
| `D:\Tools\Ollama`、`D:\cache\ollama` | Ollama 程序和模型（用户环境变量 `OLLAMA_MODELS=D:\cache\ollama`） |
| `D:\Tools\ClaudeCode` | Claude Code CLI，用个人订阅登录，供 `judge_notes.py` 调用 |
| `outputs\<运行名>` | 每轮转写的 JSON |
| `results\<运行名>` | 每轮评估的 CSV |
| `results\viewer\index.html` | 对照听写页面 |

## 3. 三个虚拟环境

依赖互相冲突，所以分成三个环境，都基于 `D:\Python311`：

| 环境 | 用途 | 关键版本 | 为什么单独分开 |
|---|---|---|---|
| `.venv` | faster-whisper 转写、生成对照页面 | faster-whisper 1.2.1，ctranslate2 4.8.4，cuBLAS 12.9，CUDA runtime 12.9，cuDNN 9.27，numpy 2.4.6 | 主环境，按 requirements.txt 安装 |
| `.venv-sci` | 用 scispaCy 抽取医学术语、跑 evaluate.py | scispacy 0.6.2，spaCy 3.7.5，en_core_sci_sm 0.5.4，jiwer 4.0.0，numpy 1.26.4 | scispaCy 要求 numpy 1.x，会把主环境的 numpy 降级 |
| `.venv-nemo` | Parakeet 转写（`--backend parakeet`） | PyTorch 2.11.0+cu128，NeMo 3.0.0，numpy 2.4.6 | NeMo 依赖很多，而且要带 CUDA 的 PyTorch |
| `.venv-hf` | Granite Speech、Cohere Transcribe（`--backend granite/cohere`） | PyTorch 2.11.0+cu128，transformers 5.21.0，accelerate 1.15 | Cohere 要求 transformers ≥ 5.4 |
| `.venv-qwen` | Qwen3-ASR（`--backend qwen3asr`） | PyTorch 2.11.0+cu128，qwen-asr 0.0.6，transformers 4.57.6 | `qwen-asr` 把 transformers 锁在 4.57，跟 Cohere 冲突 |
| `.venv-canary` | Canary-Qwen（`--backend canary-qwen`） | PyTorch 2.11.0+cu128，NeMo 3.1.0 开发版（GitHub），peft 0.21 | 要 NeMo 开发版，不能动已经能用的 Parakeet 环境 |

### 让 faster-whisper 找到 CUDA 运行库

ctranslate2 在 Windows 上要从 PATH 里找 `cublas64_12.dll` 和 `cudnn*64_9.dll`。pip 装的 NVIDIA 运行库不会自动加进 PATH，所以主环境里加了一个启动钩子：

`.venv\Lib\site-packages\_cuda_dlls.pth`

每次启动这个环境的 Python 时，它会做两件事：
- 把 `site-packages\nvidia\{cublas,cudnn,cuda_runtime,cuda_nvrtc}\bin` 加进 PATH 和 DLL 搜索路径；
- 把 `HF_HOME` 默认设为 `D:\cache\huggingface`。

加 `-I` 运行时它也照样生效。重建主环境时要记得把这个文件补回来。

另外两个环境不需要这个钩子：PyTorch 自带 CUDA 库。但 `.venv-nemo` 和 `.venv-sci` 没有这个默认设置，运行前要手动设 `HF_HOME=D:\cache\huggingface`，否则模型会下到 C 盘。

### 已验证的 GPU 功能

- faster-whisper large-v3 以 float16 在 cuda 上加载、转写都正常。50 系显卡没有报错，所以没有用到 transformers 版 Whisper 这个备选方案。
- PyTorch 2.11+cu128 能识别 sm_120，`torch.cuda.is_available()` 返回 True。Parakeet-TDT-0.6B-v2 能正常转写。

## 4. 各轮运行

| 运行名 | 数据 | 模型 | 设置 | 环境 | 状态 |
|---|---|---|---|---|---|
| `fw-large-v3` | 3 段 × 3 分钟 | large-v3 | 默认（beam 5，不开 VAD） | `.venv` | 已完成 |
| `fw-large-v3-turbo` | 3 段 × 3 分钟 | large-v3-turbo | 默认 | `.venv` | 已完成 |
| `fw-large-v3-vad` | 3 段 × 3 分钟 | large-v3 | `--vad` | `.venv` | 已完成 |
| `full10-large-v3` | 10 段完整 | large-v3 | 默认 | `.venv` | 已完成 |
| `full10-large-v3-vad` | 10 段完整 | large-v3 | `--vad` | `.venv` | 已完成 |
| `full10-parakeet` | 10 段完整，只跑合并声道 | parakeet-tdt-0.6b-v2 | 默认（全注意力） | `.venv-nemo` | 已完成（单独占用 GPU 重跑） |
| `full10-vad-nocond` | 10 段完整 | large-v3 | `--vad --no-condition-on-previous-text`（H1b） | `.venv` | 已完成 |
| `full10-vad-nocond-hst2` | 10 段完整 | large-v3 | 上一组再加 `--hallucination-silence-threshold 2`（自动打开词级时间戳） | `.venv` | 已完成 |

汇总表：`results/full10/comparison.csv`、`results/full10/top_insertions.csv`（scispaCy 术语）；`results/lexicon/full10/` 是同样的数据用自带词表算的版本。

`full10-parakeet` 的结果 JSON 里 `model` 字段写的是 `base`：当时 transcribe.py 的 parakeet 后端没有改写 `--model` 的默认值，实际用的是 `nvidia/parakeet-tdt-0.6b-v2`。之后的运行已经修好。

所有 Whisper 运行的共同设置：`language="en"`，float16，beam size 5，不加 initial prompt；是否开 VAD、是否用前文提示见上表（开发集上选定的最终设置是 VAD + 关前文提示）。三种音轨：医生声道、病人声道、合并单声道（两声道相加后峰值归一化到 -1 dBFS）。

### 测试集（47 段，只用最终设置跑一次）

| 运行名 | 模型 | 设置 | 用途 |
|---|---|---|---|
| `test47-vad-nocond` | large-v3 | `--vad --no-condition-on-previous-text`，三种音轨 | 主结果 |
| `test47-parakeet-local` | parakeet-tdt-0.6b-v2 | `--local-attention`，三种音轨 | 架构对照 |
| `test47-vad-nocond-wt` | large-v3 | 同主结果，再加 `--word-timestamps`，只跑医生和病人声道 | 给"分声道"病历按句子穿插两个声道用 |

打开词级时间戳会改变 faster-whisper 的解码窗口，所以 `test47-vad-nocond-wt` 的文字跟 `test47-vad-nocond` 不完全一样：两次运行之间约 4.4% 的词不同。但 WER 几乎相同（医生 11.2% 对 11.0%，病人 13.0% 对 13.0%），所以只是解码波动，不是质量差异。

汇总表：`results/test47/comparison.csv`。其他分析：`results/test47/overlap/`（重叠段，Whisper）、`results/test47/overlap-parakeet/`、`results/test47/negations/`（否定词）、`results/test47/listening_sample.csv`（待人工标注的 40 处插入）。对照页面：`results/viewer-test47/`。

### 规范化：原始 WER 和修正 WER

Whisper 的英文规范化器有几处不统一的写法，会被算成错误。`evaluate.py --equivalence` 在规范化之后再套一张固定的等价词表：

| 统一成 | 原写法 |
|---|---|
| okay | ok，o k，0 k（"O.K." 经规范化器会变成 "0 k"） |
| alright | all right |
| mom、mommy | mum、mummy |
| 0 | ohh、ooh（规范化器会把 "oh" 变成 "0"） |

所有运行都按两种方式各算一遍：原始结果在 `results/<运行名>/`，修正结果在 `results/equiv/<运行名>/`；主结果表（`comparison.csv`）里的 `wer` 和 `wer_corrected` 两列并列。原始 WER 用于跟文献比较，修正 WER 反映真实识别水平。人工标了"不确定"的地方造成的错误只作为上限单独报告，不从 WER 里扣除。

### 2026 年的新 ASR 模型

| 模型 | Hugging Face | 许可证 | 环境 | 安装和运行中的问题 |
|---|---|---|---|---|
| Granite Speech 4.1 2B | `ibm-granite/granite-speech-4.1-2b` | Apache 2.0 | `.venv-hf` | 无。模型卡没说明长音频怎么处理，用统一切分 |
| Cohere Transcribe 03-2026 | `CohereLabs/cohere-transcribe-03-2026` | Apache 2.0，**受限访问** | `.venv-hf` | 要用 HF 账号在模型页同意共享联系方式，并在本机 `hf auth login`（令牌存在 `D:\cache\huggingface`）。同意之后才能下载，否则 403 |
| Qwen3-ASR-1.7B | `Qwen/Qwen3-ASR-1.7B` | Apache 2.0 | `.venv-qwen` | 专用库 `qwen-asr` 锁定 transformers 4.57，跟 Cohere 冲突，所以单独建环境 |
| Canary-Qwen 2.5B | `nvidia/canary-qwen-2.5b` | CC-BY-4.0 | `.venv-canary` | 要 NeMo 开发版：`pip install "nemo_toolkit[asr] @ git+https://github.com/NVIDIA/NeMo.git"`。按模型卡装 `[asr,tts]` 会失败（tts 里的 `pyopenjtalk` 在 Windows 上要 CMake 编译）；实际只需另外 `pip install peft` |

**统一切分**：这四个模型都只适合短输入，所以用 `plan_chunks.py` 生成同一份切分方案（`outputs/chunks/test47/`）：Silero VAD 找说话区间，只在停顿处切，每段不超过 30 秒，两端各留 0.3 秒边距；超过 30 秒的连续说话在最安静的 100 ms 处切开。测试集 141 个文件切成 2482 段，最长 30.6 秒，保留 84.8% 的音频；约 0.7% 的参考词落在所有段之外（按估计的词时间算）。每段单独解码，输出的片段时间就是段的起止时间。Cohere 的处理器自己会把超过 35 秒的输入再切开，我们的段都短于这个长度，所以不会触发。

为了不把"切分方式"混进模型比较，Whisper 和 Parakeet 也用同一份切分方案各跑了一遍（`test47-whisper-chunked`、`test47-parakeet-chunked`）；原来各自的最佳设置（Whisper 自带 VAD、Parakeet 整段输入）也保留。

**逐段解码，不用批量**：`--batch-size` 可以一次解码多段，快 3–4 倍，但结果跟逐段解码不完全一致（同一文件上 Granite 有 1.6% 的词不同，Qwen3-ASR 有 0.2%），原因是批量时短段被填充到同一长度。为了让各模型可比，正式运行都用逐段（`--batch-size 1`）。

**测试集结果**（47 段，WER 为原始 → 修正；速度为每分钟音频所需秒数，RTX 5080 笔记本，逐段解码）：

| 运行 | 医生 | 病人 | 合并 | 合并：替换/删除/插入 | 合并：重叠内/外删除率 | 合并 s/音频分钟 |
|---|---|---|---|---|---|---|
| `test47-qwen3-asr-1.7b` | 9.5 → 6.1 | 10.7 → 9.5 | **11.0 → 8.6** | 5.0 / 4.2 / 1.8 | 20.3 / 2.9 | 5.5 |
| `test47-canary-qwen-2.5b` | 10.4 → 7.0 | 12.0 → 10.9 | 12.0 → 9.7 | 5.2 / 4.6 / 2.2 | 21.3 / 3.3 | 5.7 |
| `test47-parakeet-chunked` | 10.5 → 7.2 | 12.6 → 11.5 | 12.3 → 10.0 | 5.1 / 5.1 / 2.1 | 21.6 / 3.8 | 0.25 |
| `test47-vad-nocond`（Whisper，自带 VAD） | 11.0 → 7.8 | 13.0 → 11.9 | 12.5 → 10.3 | 5.0 / 5.7 / 1.9 | 25.3 / 4.1 | 5.1 |
| `test47-parakeet-local`（整段） | 11.4 → 7.9 | 14.5 → 13.4 | 12.9 → 10.7 | 4.9 / 6.2 / 1.8 | 22.7 / 4.9 | 0.16 |
| `test47-whisper-chunked` | 11.2 → 8.0 | 14.6 → 13.5 | 13.0 → 10.8 | 5.0 / 6.0 / 2.0 | 23.4 / 4.6 | 5.0 |
| `test47-cohere-transcribe` | 11.5 → 8.2 | 15.1 → 14.1 | 13.7 → 11.5 | 4.9 / 6.9 / 2.0 | 22.3 / 5.6 | 1.05 |
| `test47-granite-4.1-2b` | 12.1 → 9.0 | 23.5 → 22.5 | 14.7 → 12.6 | 4.9 / 8.4 / 1.4 | 30.3 / 6.7 | 5.5 |

- Qwen3-ASR-1.7B 三个声道都最好；医学术语错误率（合并 5.6%，Whisper 6.8%）和临床否定词丢失率（合并 2.2%，Whisper 5.0%）也最低。
- 统一切分对 Parakeet 有帮助（合并 12.9 → 12.3，病人 14.5 → 12.6），对 Whisper 略有损失（合并 12.5 → 13.0）：Whisper 自带的 VAD 切法比统一切分更适合它。
- Granite 在病人声道上有 6 处长重复（共 1372 词，如连续几百个 "no"、"yeah"），病人 WER 被拉到 23.5%；除重复外的删除率也最高。
- 重叠段：所有模型合并声道比分声道多删 10.6–13.9 个百分点，后插话的人损失都远大于正在说话的人（+15.5–20.0 对 +6.4–10.5）。这是合并声道本身的问题，换模型解决不了。
- Cohere 是四个新模型里最快的（1.05 s/分钟，Parakeet 更快），但删除偏多，病人声道尤其明显。
- 详细结果：`results/test47/comparison.csv`、`results/test47/overlap-<模型>/`、`results/test47/error_composition/`、`results/test47/negations/`。

### VAD 边距（开发集）

为检查"句首第一个词错误率高"是不是 VAD 把句首切掉了，在开发集上对比了 `speech_pad_ms` 400（默认）、800、1500 和不开 VAD（都关前文提示）：句首错误率在四组之间几乎不变（合并声道 36.1–36.8%），不开 VAD 时也一样高，所以不是 VAD 造成的。句首错误里 60% 是附和词，替换里 58% 是 "OK/okay" 这类写法差异。WER 的变化都在噪声范围内，测试集保持默认边距。结果在 `results/full10/vad_padding/`。

### 病历层面评测

1. `generate_notes.py`：本地 Ollama 跑 `qwen3:14b`（4 位量化），温度 0、固定种子、关闭思考模式，提示词版本 v3。每段问诊生成三份病历：人工转写、分声道 ASR（`test47-vad-nocond-wt`，按词级时间戳把两个声道合并成话轮并标注说话人）、合并声道 ASR（`test47-vad-nocond`，无说话人标注）。
   - 最初按句子穿插两个声道，但无前文提示的 Whisper 输出常常没有标点，"一句"会跨好几个话轮，问答被切开错位，分声道组的病历召回因此低了 3.5 个百分点。旧结果保存在 `*-separated-by-sentence` 文件夹里。
   - 噪声对照：`human_rejudge`（同一份人工版病历再评一次，测评判噪声）、`human_plain`（人工转写经 Whisper 规范化，测写法本身带来的生成波动）、`human_unlabelled_plain` 和 `asr_mixed_plain`（两边写法完全一致，只差识别出的词，测纯 ASR 错误）、`asr_separated_plain`。
   - 配对比较：`compare_notes.py`，每段问诊算一个差值，bootstrap 95% 区间，结果在 `results/notes/test47/paired_summary.csv`。
2. `judge_notes.py`：用 Claude Code CLI 非交互调用（`claude -p`，不开工具，JSON schema 输出），先把每份医生病历拆成事实清单（每段问诊只拆一次），再逐份评判候选病历。评判模型看不到病历来源，任务顺序打乱（种子 0）。每次调用记录实际模型（本轮为 `claude-opus-5-5`）。遇到服务过载会自动重试。
3. 比较时以"人工转写"组为基线：医生病历本身就和谈话有出入（例如谈话说"三到四天"，病历写"3–5 天"），所以看的是 ASR 组比人工转写组多错多少。
4. 人工抽查：`results/notes/test47/spotcheck.csv`，20 份病历的逐条评判，填 `your_label` 一列。
5. **评判流程已冻结（judge v1）**：`judge_notes.py` 里的系统提示词、拆事实和评判两个提示词、两个 JSON schema，以及 `results/notes/test47/facts/` 下每段问诊的事实清单（2026-10-26 拆分，每段只拆一次）都不再改动。之后新增的病历（新的 LLM、新的 ASR）都用同一份事实清单和同样的提示词评判。要改任何一处，就要升版本号并全部重评。判定结果 JSON 里记录 `judge_version`（v1 之前生成的文件没有这个字段，但用的是同一份提示词）。

### 复现命令（在 `D:\medical-asr-eval` 下运行）

```bash
# 数据
.venv/Scripts/python.exe -I scripts/download_data.py --out data/primock57 --limit 10
.venv/Scripts/python.exe -I scripts/prep_data.py --src data/primock57 --out data/prepared_full10 --limit 10

# 转写（Whisper）
.venv/Scripts/python.exe -I scripts/transcribe.py --data data/prepared_full10 --out outputs/full10-large-v3 --model large-v3 --device cuda
.venv/Scripts/python.exe -I scripts/transcribe.py --data data/prepared_full10 --out outputs/full10-large-v3-vad --model large-v3 --device cuda --vad

# 转写（Parakeet，只跑合并声道；需要先设 HF_HOME=D:\cache\huggingface）
.venv-nemo/Scripts/python.exe -I scripts/transcribe.py --backend parakeet --data data/prepared_full10 --out outputs/full10-parakeet --conditions mixed

# 评估（scispaCy 环境）
.venv-sci/Scripts/python.exe -I scripts/evaluate.py --data data/prepared_full10 --hyp outputs/full10-large-v3 --results results/full10-large-v3 --terms scispacy

# 汇总成对比表，并列出最长的 10 处插入
.venv-sci/Scripts/python.exe -I scripts/aggregate_results.py --results "results/full10-*" --out results/full10 --top 10

# 对照听写页面
.venv/Scripts/python.exe -I scripts/make_viewer.py --data data/prepared_3min --outputs outputs --out results/viewer
.venv/Scripts/python.exe -I -m http.server 8765 --bind 127.0.0.1
```

转写脚本支持断点续跑：已有的输出会跳过，中断后重新运行同一条命令即可。

## 5. 相对原仓库的改动

第一轮改动（PR #1、#2 已合并）：

- **`scripts/evaluate.py`**
  - 新增"重叠说话段内/段外"分析。先从 `utterances.json` 求出医生和病人发言时间重叠的区间，再把替换、删除、插入分到段内或段外，各自除以该区域的参考词数，得到错误率。结果写进 `wer.csv`、`summary.csv` 的 `ov_*`、`*_rate_in`、`*_rate_out` 列，`insertions.csv` 里新增 `in_overlap` 列。
    - 注意：词的时间是把每句话（或每个转写片段）的起止时间平均分给句中各词估出来的，不是真正的词级时间戳。
  - scispaCy 的过滤词表里加了 i、you、we 等代词，因为 en_core_sci_sm 会把 "I" 标成实体。
- **`scripts/aggregate_results.py`**（新增）：把多个结果文件夹汇总成 `comparison.csv` 和 `top_insertions.csv`。
- **`scripts/make_viewer.py`、`scripts/viewer_template.html`**（新增）：生成对照听写页面，可以听原声、看分析步骤、并排比较多种方法。
- **`transcribe.py`**：`--word-timestamps`、`--hallucination-silence-threshold`，输出里记录运行设置。

测试集这一轮新增（`test47-final` 分支）：
- **`analyze_overlap.py`**：重叠段里被丢掉的是谁、是什么词（说话人、谁后插话、谁声音小、词的类别），分声道和合并声道逐词对照。
- **`analyze_negations.py`**：所有否定词的去向（认对 / 删除 / 替换成什么），区分临床否定和话语标记，并标出重复的否定。
- **`sample_insertions.py`**：随机抽插入做人工标注，每行带对照页面的跳转链接。
- **`generate_notes.py`、`judge_notes.py`、`compare_notes.py`**：病历层面评测（见上）。
- **对照页面**：支持 `#id=…&cond=…&t=…` 深链接，`make_viewer.py` 加了 `--methods`。
- **`evaluate.py`**：`insertions.csv` 新增按词估计的时间 `t_approx_s`。
- **`bootstrap_asr.py`**：模型两两配对 bootstrap，以问诊为单位重采样，比较修正 WER、医学术语错误率和临床否定词丢失率。
- **`count_repeats.py`**：统计长重复，包括同一个词连续 ≥ 10 次，以及 2–4 词的短语连续 ≥ 5 次。
- 选定 Qwen3-ASR 的理由见 `results/test47/asr_selection.md`；第三阶段的 LLM 候选和费用估算见 `docs/stage3-llm-plan.md`。

`.claude/` 只在本机使用，不提交。

## 6. 已知问题与注意事项

- **Parakeet 长音频很慢。** 默认全注意力，音频超过约 10 分钟时显存会占满（16 GB），速度骤降：短音频几秒，14 分钟音频要 110 秒以上。测试集已改用 `--local-attention`，每分钟音频约 0.15 秒。
- **Ollama 服务要手动启动。** 托盘程序第一次启动时服务没起来，现在是直接运行 `D:\Tools\Ollama\ollama.exe serve`；电脑重启后要重新启动。跑 Qwen 时不要同时跑转写，显存不够。
- **Qwen 会编阴性发现。** 例如"无近期旅行"、"无药物过敏"，谈话里没说过；三种来源都有，评判脚本把这类计入 `extra_not_mentioned`。在提示词里举例说"不要加旅行、过敏"反而会让它写出这几项。
- **`claude -p` 的输出不完全确定。** 同一份医生病历两次拆出的事实条数略有不同，所以事实清单每段问诊只拆一次并缓存，所有来源共用。
- **GPU 不要同时跑两个模型。** Whisper 和 Parakeet 同时运行时，显存会占到 15.8/16 GB，两边都慢好几倍。这段时间测到的速度数据不能用：`full10-parakeet` 前 4 段，以及同一时段的 `full10-large-v3`。
- **large-v3 的速度比预期慢。** 显卡空闲时，每分钟音频也要大约 10 秒，GPU 利用率只有约 40%，瓶颈可能在 CPU 那一侧，还没查。这不影响 WER。
- **3 分钟那批的速度数据也不准。** 那批运行时，有游戏同时占用 GPU（约 6 GB 显存）。
- **Hugging Face 缓存不能用符号链接。** 这台电脑没开开发者模式，缓存会退回到复制文件的方式，多占一些磁盘，功能不受影响。可以设置 `HF_HUB_DISABLE_SYMLINKS_WARNING=1` 关掉警告。
- **对照页面要通过 HTTP 打开。** `python -m http.server` 不支持 Range 请求，页面里改成把整段 wav 读进内存再播放，这样才能跳转。直接双击打开 html 文件时，浏览器会拦截读取音频。
- **术语召回的两种算法不能互相比较。** 3 分钟那批用的是自带词表（约 320 个词），这一轮改用 scispaCy。
- **CSV 要用 UTF-8 写。** 中文 Windows 默认用 GBK 写文件，新模型会输出 "£" 这类符号，`evaluate.py` 写 `insertions.csv` 时报错，文件只写了一半（`wer.csv` 和 `summary.csv` 在它之前写完，不受影响）。现在所有 CSV 都按 UTF-8 写和读；旧的 3 个 GBK 文件（`full10-large-v3` 的 `insertions.csv`）已转成 UTF-8。
- **开发集比测试集难。** 开发集 10 段都来自第 1 天，WER 明显高于测试集（例如合并声道 17.2% 对 12.5%）。只看开发集会高估错误率。
