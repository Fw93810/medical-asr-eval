# 关键个案

**来源**：测试集合并声道；时间是人工转写里那句话的开始时间。

**链接**：每条链接打开对照页面，并跳到该时间。页面需要先启动本地服务，在 `D:\medical-asr-eval` 下运行：

```
python -I -m http.server 8765 --bind 127.0.0.1
```

然后访问 `http://127.0.0.1:8765/results/viewer-test47/`。

**病历列的写法**：

- 病历分格写成"生成模型 × 转写来源"，例如 27B × Whisper 指 Qwen3.8-27B 根据 Whisper 转写写的病历。
- 病历原文在 `outputs/notes-grid/notes/<模型>/<问诊>/<来源>.json`。
- 只有网格的 25 段才有病历；不在网格里的问诊（标"不在网格"）只能看 ASR 层。

## A. 否定翻转：ASR 丢了否定词

| # | 问诊 · 时间 | 原话（人工转写） | Whisper large-v3 | Qwen3-ASR-1.7B | 病历后果 |
|---|---|---|---|---|---|
| A1 | [day3_consultation03 · 280.6 s](../../viewer-test47/index.html#id=day3_consultation03&cond=mixed&t=278) 病人 | "I **don't** really have problems when going to the toilet, it's just painless." | "I would say I **really have problems** when going to the toilet it's just less so" | "I **don't** really have problems when going to the toilet. It's just been less." | **27B × Whisper** 写成 "difficulty with bowel movements (described as 'less so' frequency)"，评判把临床医生的事实"Bowels normal"判为**矛盾**。27B × 人工、27B × Qwen3-ASR 都写的是排便正常（"No diarrhea, constipation…"）。 |
| A2 | [day4_consultation08 · 322.5 s](../../viewer-test47/index.html#id=day4_consultation08&cond=mixed&t=318) 病人 | "Um, I **haven't** noticed anything like that, specifically, no." | "I noticed anything like that specifically" | "I **haven't** noticed anything like that specifically." | **被医生的复述救回**：医生紧接着说 "so you're saying you have **not** noticed morning erections"，提到这一点的病历都写对了。一问一答之后的复述，是对 ASR 否定错误的天然冗余。 |
| A3 | [day3_consultation07 · 236.6 s](../../viewer-test47/index.html#id=day3_consultation07&cond=mixed&t=236)（不在网格）医生 | "There's no temperature, no joint pains, yeah? **No fever?**" | "…no joint pains yeah **you don't know**" | "…no joint pains. Yeah. No joint pains. **No.**" | Whisper 把 "No fever?" 变成了 "you don't know"，否定和问句一起丢了。不在网格里，没有病历。 |

## B. 意思翻转

| # | 问诊 · 时间 | 原话（人工转写） | Whisper large-v3 | Qwen3-ASR-1.7B | 病历后果 |
|---|---|---|---|---|---|
| B1 | [day5_consultation05 · 128.0 s](../../viewer-test47/index.html#id=day5_consultation05&cond=mixed&t=124) 病人 | 医生问 "Are you having to go more often than normal?"，病人答 "Uh, yeah, a little bit, but I **wasn't** drinking a lot in these days." | "…but I'm **also** drinking a lot in these days" | "…but I'm **also** drinking a lot in these days." | **两个 ASR 都把 not 听成 also，意思完全相反**，而且错误直接进了病历：<br>• 14B × Whisper："drinking more than usual"<br>• 14B × Qwen3-ASR："attributed to increased fluid intake"<br>• 27B × Qwen3-ASR："attributed by the patient to high fluid intake"<br>• gpt-oss × 两种 ASR："increased fluid intake"<br>• 对照：27B × 人工写的是 "notes **reduced** fluid intake recently"<br>尿频而饮水不多，和尿频因为喝得多，是两种不同的临床意义。 |
| B2 | [day5_consultation07 · 146.6 s](../../viewer-test47/index.html#id=day5_consultation07&cond=mixed&t=143)（不在网格）医生 → 病人 | 医生："**No** vomiting, diarrhoea now?"<br>病人："No." | "…**you're vomiting** diarrhea now no…" | "Yeah, that's fine. Diarrhea now. **Yeah.**" | **两个 ASR 各错一处**：<br>• Whisper 把否定问句变成了肯定的陈述；<br>• Qwen3-ASR 丢了 "No vomiting" 和病人的 "No"，接在后面的 "Yeah" 其实是医生说的。<br>合并声道没有说话人标签，两份转写读起来都像"有吐泻"。 |

在网格的 25 段里，否定词被替换成非否定词（意思翻转）的只有 B1 这一例，Whisper 和 Qwen3-ASR 都错在同一处。在测试集 47 段里：

- Whisper 有 6 处临床否定词被替换成非否定词，Qwen3-ASR 有 5 处，见 `results/test47/negations/negation_words.csv`；
- 这些替换多是 "no" 被并进相邻的词或附和词，例如 "no pain" 变成 "okay all right"；B1 的 not → also 是两个模型唯一共有的一处。

## C. 生成模型多写的阴性发现（谈话里从没问过）

以下几条都来自**人工转写**写成的病历，与 ASR 无关。核对方法：

1. 评判把它们标为 "not_mentioned"，也就是临床医生的病历里没有；
2. 再逐段检查人工转写，确认医生和病人都没提过这个话题。

| # | 问诊 | 病历 | 病历里写的 | 转写里的情况 | 为什么危险 |
|---|---|---|---|---|---|
| C1 | [day5_consultation01](../../viewer-test47/index.html#id=day5_consultation01&cond=mixed&t=56) | gpt-oss × 人工（gpt-oss × Whisper 也有同一句） | "No nausea, vomiting, visual disturbance, abnormal smells/tastes, fever, **neck stiffness**, or other systemic symptoms." | 头痛一天、畏光。医生问过咳嗽、打喷嚏时是否加重，问过发热、皮疹，**没问过颈部**。 | 颈强直是脑膜炎的红旗征。头痛加畏光的病历里凭空写"无颈强直"，会让读病历的人以为已经排除。 |
| C2 | [day5_consultation01](../../viewer-test47/index.html#id=day5_consultation01&cond=mixed&t=56) | 14B × 人工 | "Relevant negatives: … no recent changes in vision or taste, **no recent trauma**, no recent travel…" | 同一段问诊，**没问过外伤**，也没问过旅行。 | 头部外伤是新发头痛必须问的红旗问题。 |
| C3 | [day4_consultation05](../../viewer-test47/index.html#id=day4_consultation05&cond=mixed&t=245) | 14B × 人工 | "**No significant weight loss.**" | 腹痛、腹泻、呕吐，**体重从没谈到**。病人只说因为老跑厕所，所以尽量少吃。 | 体重下降是消化道症状的红旗征。 |

**规模**：在网格里，每份病历平均多写 2.4–3.5 条阴性发现，见 `docs/stage3-grid-results.md`：

- 同一个生成模型下，不同转写来源之间差别不大，所以这类错误由生成模型决定；
- 换 ASR 解决不了。

**C 类的筛选方法**：上表是用关键词粗筛后逐条核对确认的。粗筛时有几条被排除了，因为医生其实问过相关的问题：

- day4_consultation07 的血栓；
- day1_consultation13 的避孕药；
- day5_consultation04 的血尿和手术史；
- day4_consultation01 的放射到背部。

## D. 被排除的"假"个案

- **day4_consultation05 · 408.7 s**：病人说 "I haven't, I haven't noticed any chest pain"。分析脚本把被删掉的 "not" 算作否定丢失，但删掉的只是**重复的那一个**，意思没变。
- **day3_consultation02**：临床医生的事实是 "No cold (coryzal) symptoms"（没有感冒症状），病历写的是病人"感觉冷"。病人确实说过 "I do feel cold quite a lot"。这是 cold 一词两义（感冒 / 发冷）造成的评判歧义，不是 ASR 错误。
- **day4_consultation06 · 102.0 s**：Qwen3-ASR 把医生的 "It's not ten" 写成 "Six out of ten"。病人确实说过 6 分，意思没有改变。
