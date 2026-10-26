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
| `data\primock57` | PriMock57 原始数据（目前下载了前 10 段问诊） |
| `data\prepared_3min` | 前 3 段问诊，每段裁剪到前约 3 分钟 |
| `data\prepared_full10` | 前 10 段问诊，完整长度，不裁剪 |
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

汇总表：`results/full10/comparison.csv`、`results/full10/top_insertions.csv`（scispaCy 术语）；`results/lexicon/full10/` 是同样的数据用自带词表算的版本。

Parakeet 的结果 JSON 里 `model` 字段写的是 `base`：这是 transcribe.py 的小问题，parakeet 后端没有改写 `--model` 的默认值，实际用的是 `nvidia/parakeet-tdt-0.6b-v2`。

所有 Whisper 运行的共同设置：`language="en"`，float16，beam size 5，`condition_on_previous_text=True`，不加 initial prompt。三种音轨：医生声道、病人声道、合并单声道（两声道相加后峰值归一化到 -1 dBFS）。

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

## 5. 相对原仓库的改动（未提交）

- **`scripts/evaluate.py`**
  - 新增"重叠说话段内/段外"分析。先从 `utterances.json` 求出医生和病人发言时间重叠的区间，再把替换、删除、插入分到段内或段外，各自除以该区域的参考词数，得到错误率。结果写进 `wer.csv`、`summary.csv` 的 `ov_*`、`*_rate_in`、`*_rate_out` 列，`insertions.csv` 里新增 `in_overlap` 列。
    - 注意：词的时间是把每句话（或每个转写片段）的起止时间平均分给句中各词估出来的，不是真正的词级时间戳。
  - scispaCy 的过滤词表里加了 i、you、we 等代词，因为 en_core_sci_sm 会把 "I" 标成实体。
- **`scripts/aggregate_results.py`**（新增）：把多个结果文件夹汇总成 `comparison.csv` 和 `top_insertions.csv`。
- **`scripts/make_viewer.py`、`scripts/viewer_template.html`**（新增）：生成对照听写页面，可以听原声、看分析步骤、并排比较多种方法。
- **`.claude/launch.json`**（新增）：给 Claude 桌面应用的浏览器面板启动本地服务器用。

## 6. 已知问题与注意事项

- **Parakeet 长音频很慢。** 默认全注意力，音频超过约 10 分钟时显存会占满（16 GB），速度骤降：短音频几秒，14 分钟音频要 110 秒以上。下一轮长音频建议加 `--local-attention`。
- **GPU 不要同时跑两个模型。** Whisper 和 Parakeet 同时运行时，显存会占到 15.8/16 GB，两边都慢好几倍。这段时间测到的速度数据不能用：`full10-parakeet` 前 4 段，以及同一时段的 `full10-large-v3`。
- **large-v3 的速度比预期慢。** 显卡空闲时，每分钟音频也要大约 10 秒，GPU 利用率只有约 40%，瓶颈可能在 CPU 那一侧，还没查。这不影响 WER。
- **3 分钟那批的速度数据也不准。** 那批运行时，有游戏同时占用 GPU（约 6 GB 显存）。
- **Hugging Face 缓存不能用符号链接。** 这台电脑没开开发者模式，缓存会退回到复制文件的方式，多占一些磁盘，功能不受影响。可以设置 `HF_HUB_DISABLE_SYMLINKS_WARNING=1` 关掉警告。
- **对照页面要通过 HTTP 打开。** `python -m http.server` 不支持 Range 请求，页面里改成把整段 wav 读进内存再播放，这样才能跳转。直接双击打开 html 文件时，浏览器会拦截读取音频。
- **术语召回的两种算法不能互相比较。** 3 分钟那批用的是自带词表（约 320 个词），这一轮改用 scispaCy。
- **样本量。** 10 段问诊在 PriMock57 里只占 57 段中的一小部分，都来自第 1 天，可能只涉及少数几位医生。结果只能用来跑通流程、看错误的形态。
