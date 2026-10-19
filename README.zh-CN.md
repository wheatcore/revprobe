# RevProbe

[English](README.md) | 简体中文

**把文档变更转成 AI 知识库的回归测试。**

当政策或帮助文档把“30 天”改为“14 天”，RAG 问答助手可能仍引用旧版本。RevProbe 比较两个文档版本，围绕变更事实生成测试问题，读取录制的回答或调用你的问答接口，并输出包含文档哈希、判定理由的报告，方便接入 CI。

核心功能仅依赖 Python 标准库，可完全离线运行。你也可以接入兼容 OpenAI API 的模型，让测试问题更自然；模型不能修改程序从文档中提取的旧值、新值锚点。

> **项目状态：**v0.1 原型。本项目聚焦“根据文档变更生成时效性测试”，不宣称 RAG 评测或文档版本追踪是全新概念。把生成的问题用于发布门禁前，请先人工检查。

## 快速开始

需要 Python 3.11 或更高版本。在项目根目录执行：

```bash
python -m pip install -e .
revprobe generate \
  --old examples/policy-old.md \
  --new examples/policy-new.md \
  --source support-policy \
  --output examples/probes.json
revprobe run \
  --suite examples/probes.json \
  --responses examples/answers-fresh.json \
  --output report.json \
  --markdown report.md
```

上面的新版答案示例输出为 `{"pass": 2, "fail": 0, "inconclusive": 0}`。把 `--responses` 换成 `examples/answers-stale.json`，即可看到旧答案触发失败。

退出码：`0` 表示全部通过；`1` 表示存在失败或无法判定的测试；`2` 表示输入错误或没有可检查的变更。只有明确接受无法判定的结果时，才使用 `--allow-inconclusive`。

如果无法安装包，也能直接从源码运行。在 PowerShell 中先执行 `$env:PYTHONPATH='src'`，随后把命令中的 `revprobe` 换成 `python -m revprobe.cli`；在 Bash 中使用 `PYTHONPATH=src python -m revprobe.cli`。

## 连接实际问答系统

```bash
revprobe run --suite examples/probes.json \
  --url http://localhost:8000/answer \
  --output report.json --markdown report.md
```

RevProbe 会针对每条测试发送一次 JSON `POST` 请求：

```json
{"query": "According to support-policy, what is the current rule in the 'Refund window' section?", "case_id": "038422a0215f"}
```

你的接口需要返回 JSON 对象：

```json
{"answer": "Customers can request a refund within 14 days.", "source_sha256": "27b6c8e66db6efc739c09466c92a10c5dbbe6803d0c81095f33f46f473a4645e"}
```

`source_sha256` 可省略。如果返回的是**实际引用的文档版本**的 SHA-256，即使答案措辞看起来正确，RevProbe 也能发现它引用了旧证据。设置 `REVPROBE_TARGET_TOKEN` 可为接口请求添加 Bearer Token。不要把密钥或包含敏感参数的接口地址提交到仓库。

## 可选：用 AI 生成问题

下面的命令适用于 Bash。使用无需认证的本地模型时，可以省略第一行：

```bash
export REVPROBE_API_KEY=your_key
revprobe generate --old examples/policy-old.md --new examples/policy-new.md \
  --source support-policy --output probes.json \
  --model your-model --api-base http://localhost:11434/v1
```

PowerShell 设置密钥的写法是 `$env:REVPROBE_API_KEY='your_key'`。

模型只接收发生变化的段落，每处变更返回一个 JSON 格式的问题。RevProbe 会拒绝空问题及泄露旧值或新值的问题。答案锚点和文档哈希始终由本地程序计算。模型接口须兼容 OpenAI 的 `/chat/completions`；项目没有绑定特定的云服务。

## 工作流程

```text
新旧 Markdown／纯文本文档
    → 按章节比较段落
    → 提取变化的词或数值（优先选择数值）
    → 生成可审查的问题、旧／新锚点及版本哈希
    → 读取录制答案或调用 HTTP 问答接口
    → 输出通过／失败／无法判定的 JSON 和 Markdown 报告
```

- **通过（pass）：**答案包含新锚点，且不包含旧锚点。
- **失败（fail）：**答案只包含旧锚点，或接口报告的来源文档哈希不是当前版本。
- **无法判定（inconclusive）：**没有答案、答案格式错误、同时包含新旧锚点，或两个锚点都没有。默认情况下，模糊答案不会被算作通过。

报告会记录问题、锚点、答案、接口提供的来源版本和机器可读的判定理由。测试集与报告均带有 schema 版本号。

## 适用范围与局限

RevProbe 目前最适合检查**稳定 Markdown 标题下，数值或简短规则的变更**。它会配对同一标题下的变更段落；如果找不到明确不同的新旧词语，就跳过该变更。

它不会判断任意改写在语义上是否等价，不会证明答案符合现实事实，也不解析 PDF。它无法独立核实问答接口是否如实报告了引用版本。数值锚点采用完整词匹配，但如果同一数值在答案的其他位置出现，结论仍可能无法判定或产生误导；发布前应检查测试用例和实际答案。AI 生成的问题也可能不准确。

生产环境中，建议在检索元数据里保存可信的文档版本，并由问答接口返回实际引用的版本。复杂政策变更应补充人工审查的测试问题。未经允许，不要把机密文档发送给第三方模型。

## 开发与测试

```bash
python -m unittest discover -s tests -v
```

[实施计划](docs/plans/2026-10-19-revprobe.md)记录了设计；[贡献指南](CONTRIBUTING.md)说明了如何添加测试和适配器。

## 相关项目

RAG 可靠性和引用测试已有不少研究与工具：[RAGProbe](https://github.com/AntonGlenbovitch/ragprobe)关注数据集与模型配置评估；[ragcitecheck](https://github.com/ppon1086/ragcitecheck)关注不同运行间的引用稳定性。RevProbe 的切入点是直接从文档版本变更生成小型、可审查的测试，并检查助手是否停止使用被取代的旧事实。这些项目可以互补；这里不作穷尽的原创性声明。更详细的对比见[项目定位](docs/landscape.md)。

## 简历描述示例

> 开发开源 Python CLI 工具 RevProbe，将政策文档版本变更转化为 RAG 问答系统的定向回归测试；实现章节级差异分析、可选的 LLM 问题生成、来源版本哈希校验、HTTP／离线测试接口、可解释判定报告及 CI 测试。

## 开源许可证

采用 MIT 许可证，详见 [LICENSE](LICENSE)。
