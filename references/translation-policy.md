# 专业视频中文字幕与知识提炼质量规范

## 字幕
1. 输入以英文原始文字和时间戳为准；不得改变条目 ID、起止时间、次序，不能擅自合并/拆分。
2. 英文术语第一次出现采用 `中文（English）`，后续可使用统一简称；术语见 `glossary.tsv`。
3. Linux API/符号应原样保留：`dma_map_single()`、`struct device`、`CONFIG_PREEMPT_RT`、`regmap_read()`、`RK3568`、`I2C`、`GPIO` 等。
4. 命令、路径、文件名和内核日志不可意译；口语赘词可以精炼，但不能省略否定、前提、限定条件、版本号或数值。
5. 字幕通常 1-2 行，中文单行推荐 16-20 字左右；技术名称较长可适度扩展，不通过篡改术语强行缩短。
   `validate` 默认对每行超过 28 个非空白字符、全条超过 24 CPS 提示复核，时长超过 12 秒也告警；阈值可配置，已换行字幕按各行检查，不用全条字数冒充单行宽度。字幕仍需在目标播放器上检查。
6. 语言识别不确定时，需单独备注：`[待核对：原语音/幻灯片]`，并提醒人工核实。
7. 翻译应考虑相邻片段上下文，不逐句独立翻译造成指代不明；仍保持 ID 数不变。
8. 翻译缺失/空字符串/不匹配 ID 视为失败；英文大量残留应报告供校对，不通过机械替换隐瞒问题。
9. `translations.json` 携带翻译开始时源稿的 `source_fingerprint`；换源后不得将旧译文重盖新指纹。关键令牌全片/局部缺失、字幕重叠或重复循环由 `quality-report.json` 定位，须回查原文或原音后决定是否修订，不能机械去重。

## 结构化技术笔记

仅在用户需要讲义/总结时读取 [课程分析方法](analysis-policy.md)，其中统一规定摘要深度、章节提取、证据标记、全课综合与验收。翻译任务不必额外生成笔记。

## 课程常见歧义
- interrupt handler vs threaded IRQ：区分硬中断处理和线程化中断。
- DMA coherent vs streaming mapping：不能等同于完全不需要缓存同步。
- device tree binding：设备树约束/绑定，不能误解为总线驱动绑定。
- suspend vs hibernation：挂起和休眠（磁盘休眠）不应混用。
- probe deferral vs probe failure：延迟探测与永久失败不同。
- URB vs URC：USB Request Block 与 Unsolicited Result Code 完全不同。
