<div align="center">
  <img src="logo.png" alt="banner Logo" width="800">
</div>

# before-submit

[English](README.md) · [GitHub 仓库](https://github.com/thinkwee/BeforeSubmitSkill)

**一个用于投稿前检查学术论文的 Claude Code skill。**

它会检查那些容易导致论文被 desk reject 或在审稿中暴露问题的细节：伪造、幻觉或已撤稿引用，LaTeX 错误，双盲身份泄露，以及目标会议规则违规（页数限制、必需章节、必需 checklist 等）。最终会生成一份按优先级排序的报告，也可以选择生成干净的 HTML 视图，并且**不会在未经你确认的情况下修改文件**。

> 这是为 LLM agent 时代准备的投稿前检查工具：AI 写作工具可能会编造看似合理但并不存在的参考文献，也可能留下对话痕迹。`before-submit` 会用真实数据库核验每条参考文献；无法直接索引的条目会交给 agent 进行网页搜索确认，同时继续扫描源码中的其他风险。

---

## 检查内容

**参考文献**

- ✅ **存在性与元数据**：并行使用 CrossRef、Semantic Scholar、OpenAlex、DBLP 和 arXiv 核验每条记录，并进行多源交叉确认。无法核验的条目会升级为 agent 网页搜索，因此真正伪造的引用会被明确标出。
- 🚫 **撤稿检查**：检查 DOI 是否存在 retracted、withdrawn 或 expression of concern 状态。
- 📄 **优先引用正式发表版本，而不是 arXiv**：如果预印本已有会议或期刊版本，会被标记、经网页确认，并提示应引用的正式版本。
- 🔁 **重复条目、未使用条目、缺失 `\cite` key、条目类型必需字段、预印本比例**，以及可选的死链检查。
- 🎯 **引用相关性（可选）**：判断该引用是否真的支撑正文中的对应论断，由 agent 自身完成判断，不需要额外 API key。

脚本标记出的每条参考文献问题，都会由 agent 再通过实时网页搜索确认后才进入最终报告：脚本负责初筛，agent 负责判断。

**LaTeX 与写作质量**

- 检查 caption 位置（按会议规则）、交叉引用、引用格式、公式、**AI 文本痕迹**、**语法与机械错误**、过弱或模糊表述、术语一致性、**缩写规范**（先定义再使用、不重复定义、不冲突定义）、**引用名词一致性**（如 "Figure 3" 与 "fig. 3"，`Fig.`/`Sec.`/`Eq.` 风格）、数字格式、en-dash 范围、直引号/弯引号、编码乱码等。
- 写作检查由 **agent 像审稿人一样阅读组装后的正文**完成，而不是硬编码 linter；grep 只用于定位机械问题，语义类检查（语法、术语、缩写语义、引用契合度）由 agent 判断。
- **双盲匿名检查**：作者泄露、可识别 URL、致谢、自我暴露式措辞；只针对 review 版本检查。

**内部一致性**（论文与自身内容互相核对）

- 🔢 **正文数字是否匹配表格**：正文和摘要中的数字 claim 会与实际 `tabular` 单元格交叉核对，并考虑四舍五入、子集、指标容差，同时结合周围的 LaTeX 上下文（表头、行标签、共享宏）判断是真不一致还是看起来不一致，避免误报；关键 headline 数字错误会升级。
- 📊 **表格是否自洽**：加粗的 "best" 是否真的是最佳，合计是否正确，ablation 差值是否一致。
- 🖼️ **图是否匹配正文描述**：读取 PNG/JPG/PDF 图文件，比较曲线趋势、坐标轴、图例与正文说法是否一致；无法读取的图（如 EPS）会被记录，但不会臆测。
- 🔗 **跨章节一致性**：同一指标在不同位置的数值是否一致，论断是否指向正确的表、图或附录。

**会议规则合规性**（ACL · EMNLP · NAACL · CVPR · ICCV · ECCV · NeurIPS · ICML · ICLR）

- 页数限制、必需章节（例如 ACL **Limitations**）、必需提交物（例如 **NeurIPS Paper Checklist**、ICML Impact Statement / Type-1 fonts）、style file、纸张大小、caption 规范。
- **优先实时规则**：在线时获取会议当前 Call for Papers；离线时回退到内置快照，并明确说明使用了哪一种来源。

**可选编译检查（仅 pdflatex）**

如果有 TeX Live `pdflatex` 工具链，或你允许安装轻量且与 Overleaf 一致的 **TinyTeX**，它会编译论文并读取日志，权威检查 undefined references/citations、重复 label、overfull boxes，以及真实页数是否超出会议限制。若没有 pdflatex 且你拒绝安装，则编译与页数检查会被**跳过并明确记录**；它不会用 Tectonic/XeTeX 等其他引擎替代，因为那会导致与 Overleaf 不一致的页数。

检查会以**并行 agent 团队**运行（参考文献 · LaTeX 与写作 · 会议合规 · 内部一致性 · 编译），每个 agent 生成自己的报告片段，最后合并。**任何问题都不会只凭一次检测就上报**——每个被标记的问题都会先结合上下文做一次独立复核（参考文献用实时网页搜索、数字/图表不一致会重读两侧、语法判断会再看一遍）。结果写入 **`before-submit-report.md`**，按 🔴 desk-reject 风险、🟠 审稿人会皱眉、🔵 可选润色 分组，**每条都标注 `file:line` 并附上原始 `.tex` 源码引用**；也可以渲染为最小、自包含的 **HTML** 视图。

---

## 安装

### 方式 A：作为插件安装（推荐）

在 Claude Code 中运行：

```text
/plugin marketplace add thinkwee/claude-plugins
/plugin install before-submit@thinkwee
```

开启一个新会话，然后直接让 Claude *"run before-submit on my paper"*，或从 `/` 菜单中选择该 skill。

### 方式 B：作为个人 skill 手动安装

```bash
git clone https://github.com/thinkwee/BeforeSubmitSkill.git
cp -r BeforeSubmitSkill/skills/before-submit ~/.claude/skills/before-submit
```

重启 Claude Code 后，该 skill 就会在所有项目中可用。

---

## 使用方法

可以指向一组 `.tex`/`.bib` 文件，也可以指向整个 LaTeX 项目目录。第一次运行时会快速询问几个问题：

1. 是 review（双盲）版本还是 camera-ready 版本？
2. 目标会议、年份和 track 是什么？
3. 是否运行引用相关性检查？默认是 yes。
4. 是否允许自动应用安全的机械修复，还是每个修改都以 diff 形式征求确认？

之后它会组装项目（跟踪 `\input`/`\include`，解析每个 `.bib`），解析会议规则，将检查分发给并行 agent 团队，每个 agent 持续写入自己的报告片段，最后合并并提供 HTML 视图。**除非你批准具体修改，否则源文件不会被改动。**

---

## 需求

- **Claude Code**，并支持 skills/plugins。
- **Python 3.8+** 用于内置脚本；只使用标准库，**不需要 `pip install`**。
- *可选*：TeX Live **`pdflatex`** 工具链，用于编译类检查。它与 Overleaf 使用的引擎一致，因此页数匹配。没有安装时，skill 会询问是否安装轻量、Overleaf 一致的 **TinyTeX**；即使没有也能工作，只会跳过编译和页数检查，并且不会换用其他引擎。
- *可选*：网络连接，用于数据库核验和实时 CfP 获取；离线时会优雅降级。可以设置 `BEFORE_SUBMIT_CONTACT_EMAIL` 和 `SEMANTIC_SCHOLAR_API_KEY` 来提高 API rate limit。

---

## 工作方式

```text
skills/before-submit/
├── SKILL.md            # 编排逻辑：顺序准备 + 并行审查团队
├── reference/          # 按阶段按需加载
│   ├── venues.yaml     # 离线会议规则快照（在线时实时 CfP 优先）
│   ├── venue-rules.md  ·  bib-checks.md  ·  latex-checks.md
│   ├── faithfulness-checks.md  ·  compile-checks.md  ·  report-format.md
└── scripts/            # 仅标准库，可用 python3 直接运行
    ├── assemble_project.py   # 查找主 .tex，跟踪 include，映射 .bib
    ├── verify_refs.py        # 并行多源参考文献核验器
    └── report_to_html.py     # 将报告 markdown 渲染为单文件 HTML
```

`SKILL.md` 保持精简，只告诉 agent 每个阶段需要读取哪份 reference 文件；详细检查目录和数据只在需要时加载。

---

## 参与贡献

欢迎贡献，尤其是**维护 `reference/venues.yaml` 的时效性**和**添加新会议**。数据结构和新增检查方式请见 [CONTRIBUTING.md](CONTRIBUTING.md)。如果 `before-submit` 帮你避免了投稿事故，也欢迎给 [GitHub 仓库](https://github.com/thinkwee/BeforeSubmitSkill) 一个 star，方便更多人发现它。

## 许可证

[MIT](LICENSE) © 2026 thinkwee
