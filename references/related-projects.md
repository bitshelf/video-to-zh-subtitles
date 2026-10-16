# 其他视频翻译、总结 Skill 与工具链接（维护监测清单）

核查日期：**2026-10-15**。以下是官方 GitHub 仓库/官方 Skill 文件，不含第三方镜像。`活跃`指截至核查日发现 2026 年的发布记录或可见维护证据；这不是代码安全审计或服务质量保证。**Skill 与完整应用/库单独分类**。

## A. 现成 Agent Skills（可借鉴，维护活跃度未充分证实）

| 仓库 / Skill | URL | 适用能力 | 核查判断 |
|---|---|---|---|
| oomol-lab/video-subtitle-translator | https://github.com/oomol-lab/video-subtitle-translator | 转录、字幕翻译、SRT/ASS、封装视频 | 仓库可访问、12 commits；小型项目，近期稳定维护证据不足；需要 OO CLI 与 Fusion API；慎用 |
| fuleinist/video-to-skill | https://github.com/fuleinist/video-to-skill | 视频转可复用技能、字幕、Whisper、视觉帧 | 仓库可访问；活跃度和实际质量需自行复核 |
| Ppang0405/youtube-transcribe-skill | https://github.com/Ppang0405/youtube-transcribe-skill | yt-dlp + Whisper + 总结 | Skill 文件可访问；活跃度尚未核实 |
| madhancr/youtube-summarizer-skill | https://github.com/madhancr/youtube-summarizer-skill | YouTube 摘要和调研 | Skill 文件可访问；活跃度尚未核实 |
| martinopiaggi/summarize | https://github.com/martinopiaggi/summarize | 多来源视频转录和总结，内含 `.agent/skills/summarize/SKILL.md` | 约 233 commits、项目有测试/CHANGELOG；近期发布频度未确定 |
| ricoisme/vscode-agents translate-srt | https://github.com/ricoisme/vscode-agents/blob/main/skills/translate-srt/SKILL.md | 翻译 SRT、双语字幕 | 可作为规则参考；活跃度未核实 |

**不要把上表统称为“积极维护”。** 目前没有足够公开证据对这些小型 Skill 逐一做出长期活跃结论。使用前检查 `commits`、`releases`、`issues` 和依赖情况。

## B. 维护迹象明确的上游工具（推荐作为 Skill 后端）

| 项目 | 官方 URL | 能力 | 维护证据 / 截至核查日 |
|---|---|---|---|
| yt-dlp | https://github.com/yt-dlp/yt-dlp | 公开在线视频元数据/字幕/媒体获取 | 官方 Release `2026.08.19`（2026-08-19） |
| pyVideoTrans | https://github.com/jianchang512/pyvideotrans | ASR、字幕翻译、双语字幕、视频处理 | 官方 Release `windows-v4.15`（2026-10-04）；带 CLI/WebUI/测试 |
| WhisperX | https://github.com/m-bain/whisperX | 精细时间戳对齐/说话人区分 | 官方 Release `v3.8.6`（2026-05-25），另有 6 月预发布 |
| faster-whisper | https://github.com/SYSTRAN/faster-whisper | 本地语音转录 | Releases 页面显示 1.2.1/1.2.0；本次未核实其 2026 年最后一次发布时间，建议继续关注 |
| VideoLingo | https://github.com/Huanshere/VideoLingo | 字幕切分、翻译、对齐、配音 | 大型公开项目、约 1,091 commits；本次未确认近期 Release 日期，关注但暂不标注持续活跃 |
| Subtitle Edit | https://github.com/SubtitleEdit/subtitleedit | 字幕人工编辑与同步 | 上游可访问；本次未确认最新版本日期 |

## C. Agent Skills 生态/安装规范

- Agent Skills 官方规范：https://agentskills.io/specification
- Agent Skills 官方规范源码：https://github.com/agentskills/agentskills
- Anthropic Skills 示例仓库：https://github.com/anthropics/skills

## 维护判断的注意事项

- `stars`、`forks`、累计 commits 不能替代“近期在维护”。
- 下载脚本不要盲目运行不可信仓库的安装命令；先看依赖、许可证、是否上传视频到第三方。
- 如果只是为了掌握更可靠的字幕/ASR，优先选择有真实 Releases、明确依赖和回归测试的后端工具。
- GitHub URLs 为项目官方仓库；没有把第三方项目源码复制到此 Skill 中，因此无需继承这些项目的代码许可证。
