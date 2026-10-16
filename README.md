# video-to-zh-subtitles

英文技术视频 → 中文字幕的可移植 Agent Skill：**字幕生成**（英文字幕提取 / 本地 ASR，可选）＋**字幕翻译为中文**（LLM API 或人工 Agent），面向 Bootlin、Linaro、Linux Foundation、ELC 等英文技术课程，产出中文字幕 / 双语字幕 / 术语表 / 技术笔记。

> **实现边界**：本包提供可运行的本地 CLI；没有自动部署 ASR 模型、没有内置远程 LLM 配额、不承诺所有平台视频都可下载。没有视频或测试数据时不能声称翻译质量已经通过真实课程验证。

## 1. 安装

Python 3.10 或更新版本（建议 Python 3.11+）。导入/转换 `.srt` 和 `.vtt` 不需要第三方 Python 库。

```bash
unzip video-to-zh-subtitles.zip
cd video-to-zh-subtitles
python3 scripts/video_learning.py doctor
```

可选下载/识别（建议 venv）：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'yt-dlp>=2026.8.19' 'faster-whisper>=1.2.0'
# Debian/Ubuntu
sudo apt-get install ffmpeg
```

说明：ffmpeg 是处理本地视频/音频和 VTT 字幕封装的常用工具；运行 faster-whisper 时也需处理模型下载、CPU/GPU 依赖。不要将 PyTorch/CUDA 驱动版本写死。

### 安装给 Agent

```bash
mkdir -p ~/.agents/skills
cp -a video-to-zh-subtitles ~/.agents/skills/video-to-zh-subtitles
# 对于 Claude Code，可复制到 ~/.claude/skills/video-to-zh-subtitles
# 对于 Codex CLI，优先使用 ~/.agents/skills/video-to-zh-subtitles
```

Pi 和 OpenCode 的 Skill 发现目录取决于版本/配置；先运行其最新文档中的 Skill 扫描规则，可使用软链接指向此目录。不要为了安装把目录里所有脚本当作第三方代码安装到系统 PATH。

## 2. 最小可用：已有 SRT（不需要联网）

```bash
python3 scripts/video_learning.py import lecture.en.srt --out ./output/lecture
python3 scripts/video_learning.py outline --out ./output/lecture
python3 scripts/video_learning.py validate --out ./output/lecture
```

生成 `transcript.json`、`transcript.en.srt` 和结构化笔记模板 `notes.zh.md`；此时**尚未生成中文翻译**，校验会给出待翻译状态。

## 3. 在线视频字幕优先

```bash
python3 scripts/video_learning.py fetch 'https://www.youtube.com/watch?v=VIDEO_ID' --out ./output/lecture
```

`fetch` 仅尝试获取英文人工/自动字幕和元数据，不会默认下载视频。如果不可用，应下载已获授权的视频或音频，并执行 `transcribe`：

```bash
python3 scripts/video_learning.py transcribe ./lecture.mp4 --out ./output/lecture --model medium --device cpu
```

可选参数：`--device cpu|cuda|auto`，`--compute-type int8|float16|float32|auto`。对技术术语密集的课程，建议使用更高质量的模型，并人工校对 API 名称。

默认模型为 `medium`，优先考虑技术课程的转录质量，同时需要比 `small` 更多的内存与计算时间。资源受限或只想快速试跑时显式选择 `--model small`。先用术语密集、噪声和口音有代表性的短片段试跑，再处理全场；更大模型仍可能误识别 API、寄存器和缩写。

| `--model` | 上游参考相对速度 | 质量与使用取舍 |
| --- | --- | --- |
| `small` | 约 4× | 小模型，适合资源受限或初步试跑；技术术语需重点校对 |
| `medium`（默认） | 约 2× | 本项目技术讲座的默认折中；仍需与更大模型做片段对照 |
| `turbo` / `large-v3-turbo` | 约 8× | 上游称相对 large-v3 加速明显、精度略降，可试用于长场转录 |
| `large-v3` | large 系列参考基准约 1× | 质量优先的候选，计算资源需求较高；不保证每段都优于其他模型 |

速度列引用 [Whisper 官方模型表](https://github.com/openai/whisper#available-models-and-languages)，是其在 **A100、英文语音、相对 large 模型**的近似参考，不是本 CLI、faster-whisper 或 CPU 的实测速度，也不是实时倍率；上游未在该表提供技术讲座准确率。本项目未复测各模型的术语错误率。`turbo` 和 `large-v3-turbo` 的后端别名见 [faster-whisper 模型映射](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/utils.py)。

## 4. 翻译（LLM API 或人工 Agent）

### OpenAI 兼容 API

```bash
export VIDEO_LLM_BASE_URL='https://api.openai.com/v1'
export VIDEO_LLM_API_KEY='your-key'
export VIDEO_LLM_MODEL='YOUR_MODEL'
python3 scripts/video_learning.py translate --out ./output/lecture --batch-size 20
python3 scripts/video_learning.py analyze --out ./output/lecture
python3 scripts/video_learning.py validate --out ./output/lecture
```

默认调用 OpenAI 风格的 `POST /chat/completions`，使用 Python 标准库联网；不保证所有兼容服务支持完全相同的 JSON 响应形态。失败时保留已有中间结果，报告错误；不静默生成假译文。

### 课程拆解与学习笔记

借鉴图书摘要的分层输出和拆书的框架提取方法，先识别课程问题与主线，再提取带时间码的章节证据，最后综合为全课笔记。具体规则见 [课程分析方法](references/analysis-policy.md)，来源与适配取舍见 [方法参考](references/summary-methods.md)。

```bash
python3 scripts/video_learning.py analyze --out ./output/lecture --depth quick
python3 scripts/video_learning.py analyze --out ./output/lecture --depth standard
python3 scripts/video_learning.py analyze --out ./output/lecture --depth deep --chunk-chars 10000
```

- `quick`：主线、关键结论、适合谁学、回看点。
- `standard`（默认）：课程地图、章节要点、机制、案例、适用边界、术语和复习问答。
- `deep`：增加概念依赖、方案取舍、实践步骤、预期观察与验收方法；练习属于编辑设计，不能冒充已执行实验。

`analyze` 先逐块生成信息卡，再综合去重；摘要较长时分组逐层综合，最多 6 层。`--chunk-chars` 限制转录块的字符数，综合输入上限为其两倍；这不是模型 token 限制，不包含提示词开销，需按服务上下文容量调整。模型未按要求压缩、摘要无法分组或超出上限时会停止，避免无限追加调用。综合会增加 API 调用和费用。

每次运行的来源指纹、信息卡及综合稿保存在 `<out>/analysis/run-*/`。失败时保留中间结果与原有 `notes.zh.md`；可由 Agent 根据保存的信息卡继续整理，重新运行命令则会重新调用 API，并不会自动续跑。成功时覆盖 `notes.zh.md`，已人工编辑的笔记应先备份。

无独立 API 时，Agent 按相同方法直接整理 `notes.zh.md`；`outline` 仅生成待填写框架。仅需笔记时不必先翻译字幕，仅需字幕时不必生成笔记。按内容调整章节和例子数量，原稿没讲到的版本、案例或演示结果须明确缺失。

### Agent 自行翻译（无 API）

编辑 `output/lecture/translations.json`：

```json
{
  "source_fingerprint": "从翻译开始时的 transcript.json 复制实际指纹",
  "items": [
    {"id": 1, "text": "这是第一个中文字幕片段。"},
    {"id": 2, "text": "这是第二个中文字幕片段。"}
  ]
}
```

```bash
python3 scripts/video_learning.py import-translations ./output/lecture/translations.json --out ./output/lecture
python3 scripts/video_learning.py validate --out ./output/lecture
```

字幕会生成 `.zh.srt`、`.bilingual.srt` 和 `.bilingual.ass`。`ASS` 双语显示依赖播放器字体配置，建议在播放器上实测。

`translate` 和 `import-translations` 均支持 `--order zh-first|en-first`，默认 `zh-first` 保持中文在上。指定 `--order en-first` 时，双语 SRT 和 ASS 都显示英文在上、中文在下；ASS 仍使用中文 46px、英文 32px，纯中文字幕和时间轴不变。重新导出时需再次指定顺序：

```bash
python3 scripts/video_learning.py import-translations ./output/lecture/translations.json --out ./output/lecture --order en-first
```

每场视频可以在 `<out>/glossary.local.tsv` 放置本场术语表，沿用全局表的 TSV 格式（英文、中文建议、可选说明，表头可选）。按英文条目忽略大小写合并，本场条目整行覆盖同名全局条目，其余全局条目保留。API 翻译与术语校验使用同一合并结果；Agent 翻译也需读取本场表。说明以 `保留 ` 开头时，后面的令牌进入受保护术语检查：

```tsv
English	中文建议	说明
eMMC	嵌入式多媒体卡	保留 eMMC
inode	索引节点	保留 inode
```

术语表不再静默截断到 8000 字符；全表会发送到所选翻译服务，若超出模型上下文，应精简本场规则或选择足够上下文的模型。仅记录数据绑定的源指纹不包含术语表；中途修改术语表不会自动重译已完成批次，需人工检查一致性。

`transcript.json` 在导入时附有 `source_fingerprint`，译文必须携带翻译开始时的指纹。更换 ASR 模型或修订原稿后，即使条数和 ID 不变，旧指纹也会导致拒绝导入。不要在导入旧译文时重新计算并替换指纹；它只能证明数据绑定，不能证明翻译语义正确。旧格式缺少指纹时默认拒绝；确已核对来源关系时可显式加 `--allow-unbound`。该选项不接受错误指纹。

### 字幕质量检查

```bash
python3 scripts/video_learning.py validate --out ./output/lecture --for subtitles --require-complete
python3 scripts/video_learning.py validate --out ./output/lecture --for subtitles --max-duration 12 --max-line-chars 28 --max-cps 24
# 仅笔记用 --for notes；默认 --for all 检查两种交付物。
```

导入（包括 `fetch`）、ASR 和译文导出都会刷新 `quality-report.json`；`validate` 可按当前交付范围重新检查。普通质量警告保留产物且命令成功，`--require-complete` 对当前范围内的警告返回失败。源指纹或译文结构错误在 `validate` 中始终失败，并保留错误报告。

- **时间轴**：检查重叠，包含长字幕覆盖后续多条的情况；默认持续超过 12 秒提示复核，可用 `--max-duration` 调整。重叠可能是刻意设计，长字幕也未必错误，因此不直接拒绝导入或自动裁剪。非法时间跨度、非有限时间值和空转录仍直接拒绝。
- **可读性**：默认译文每行超过 28 个非空白字符报 `line_width`，全条字符数除以时长超过 24 CPS 报 `reading_speed`；可用 `--max-line-chars`、`--max-cps` 调整。分别检查已换行的各行，移除常见 SRT 样式标签并解码 HTML 实体；中英文、数字和标点各按字符计数，这是启发式字符数而非像素宽度。CPS 统计全条所有行；双语同时阅读的额外负担未计入。只提示，不自动断行、删内容或改变时轴。
- **重复循环**：相邻字幕词集合相似度至少 0.85、与本轮首条也至少 0.85、至少 5 个不同英文词、条间间隔不超过 2 秒，连续达到 5 条即报告整个疑似循环及 ID/时间范围。真实重复和滚动字幕也可能触发；短句、短循环、长间隔及段内重复可能漏检。先回听再修稿，不自动删除。
- **术语完整性**：检查含数字、斜线、下划线、内部混合大小写及大写缩写的令牌，以及术语表中“保留 …”条目；关联检查 `40 KB` 等数值与单位，允许 `40KB` 空格差异。先查全片缺失，再查各出现处前后两条字幕的译文窗口。匹配考虑 ASCII 令牌边界，中文紧邻术语可通过；局部缺失仅提示人工复核，正常改写或更远的跨条表达也可能触发。此启发式检查不等于术语或数值全面正确。

ASR 显式使用 `condition_on_previous_text=False` 降低跨窗口循环风险，温度回退为 `(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`，静音阈值保留 `0.6`。关闭前文条件可能降低跨窗口一致性；调高静音阈值会让片段更难满足静音判定，不能作为通用防幻觉措施。参见 [faster-whisper 参数说明](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)。无告警不代表视频全部语音均被正确转录。

导入、转录和导出时的自动报告使用默认阈值；`validate` 使用本次指定阈值，并将其记入报告的 `thresholds` 字段。质量阈值必须为有限正数。翻译各批次复用启动时计算的源指纹，导出前重新读取并校验一次源稿；如处理中换源，则拒绝导出并保留原指纹对应的部分缓存。

## 5. 转录与总结的责任界限

- 英文原始字幕质量差会直接影响翻译和总结，优先使用讲者上传的字幕，并与视频/PPT 对照。
- API 翻译会发送转录文本至所配置服务；隐私敏感资料应先确认服务政策，或使用自托管兼容 API。
- 本 CLI 的 `analyze` 是**基于转录文本**的时间戳分析，不会凭空检索内核源码。一手资料需要由 Agent 单独检索后补充，并注明出处。
- 翻译分批处理会保留已完成数据，以便失败后恢复；输出可人工校对后再次生成。
- 使用视频在线下载功能前，请遵守来源网站的服务条款和版权许可。

## 6. 运行自检

```bash
python3 -m unittest discover -s tests -v
python3 scripts/video_learning.py --help
```

所有文本文件和测试读取均显式使用 UTF-8。Windows 的默认文本编码取决于 Python 版本、UTF-8 模式和系统设置；为让重定向输出与读取工具一致，可在运行前启用：

```bat
set PYTHONUTF8=1
py -m unittest discover -s tests -v
py scripts/video_learning.py doctor
```

PowerShell 使用 `$env:PYTHONUTF8='1'`。如果终端或下游程序按 GBK 解码 UTF-8 输出，仍需将其改为 UTF-8；不强制改写所有调用方的控制台编码。不为特定沙箱绕过目录/文件权限，写入被拒时应使用获准目录；原子写入继续采用临时文件加替换。

## 7. 保存其他项目的链接

见 [`references/related-projects.md`](references/related-projects.md)；按 **Agent Skill / 视频处理应用 / 基础组件** 分类，并且将有发布证据与仅有 GitHub 仓库的项目区别标注。维护状态会随时间变化，该文件不是自动更新的实时榜单。
