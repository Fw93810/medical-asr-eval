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

### 病历层面评测

1. `generate_notes.py`：本地 Ollama 跑 `qwen3:14b`（4 位量化），温度 0、固定种子、关闭思考模式，提示词版本 v3。每段问诊生成三份病历：人工转写、分声道 ASR（`test47-vad-nocond-wt`，按词级时间戳把两个声道合并成话轮并标注说话人）、合并声道 ASR（`test47-vad-nocond`，无说话人标注）。
   - 最初按句子穿插两个声道，但无前文提示的 Whisper 输出常常没有标点，"一句"会跨好几个话轮，问答被切开错位，分声道组的病历召回因此低了 3.5 个百分点。旧结果保存在 `*-separated-by-sentence` 文件夹里。
   - 噪声对照：`human_rejudge`（同一份人工版病历再评一次，测评判噪声）、`human_plain`（人工转写经 Whisper 规范化，测写法本身带来的生成波动）、`human_unlabelled_plain` 和 `asr_mixed_plain`（两边写法完全一致，只差识别出的词，测纯 ASR 错误）、`asr_separated_plain`。
   - 配对比较：`compare_notes.py`，每段问诊算一个差值，bootstrap 95% 区间，结果在 `results/notes/test47/paired_summary.csv`。
2. `judge_notes.py`：用 Claude Code CLI 非交互调用（`claude -p`，不开工具，JSON schema 输出），先把每份医生病历拆成事实清单（每段问诊只拆一次），再逐份评判候选病历。评判模型看不到病历来源，任务顺序打乱（种子 0）。每次调用记录实际模型（本轮为 `claude-opus-5-5`）。遇到服务过载会自动重试。
3. 比较时以"人工转写"组为基线：医生病历本身就和谈话有出入（例如谈话说"三到四天"，病历写"3–5 天"），所以看的是 ASR 组比人工转写组多错多少。
4. 人工抽查：`results/notes/test47/spotcheck.csv`，20 份病历的逐条评判，填 `your_label` 一列。

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
- **开发集比测试集难。** 开发集 10 段都来自第 1 天，WER 明显高于测试集（例如合并声道 17.2% 对 12.5%）。只看开发集会高估错误率。
