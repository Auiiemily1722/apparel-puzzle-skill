# AGENTS.md — 服饰印花拼图技能项目（apparel-puzzle-skill）

> 本文件是项目的 **agent 行为手册**。任何 agent 接手本项目：先读 `NAVIGATION.md`（顶层地图）→ 再读本文件。
> 执行任务以本文件 + `skill/SKILL.md` + `config/skill.config.json` 为事实来源，不要依赖对话历史中的外部说明。

---

## 一、这个项目是做什么的

用户在本项目的对话窗中**直接发送透明底 logo 图（1~2 个，可附带 1 张字符图）+ 衣服原图**（无需任何文字指令）时，agent：

1. **先用视觉能力识别角色**：判断哪些图是 logo（透明底图案/品牌标）、哪张是衣服原图；
2. **智能布局**：logo 组合放**左侧大图**（主 logo 在上、字符在下的垂直堆叠；若为两个 logo 则 50:50 按 logo 现状智能排布），衣服原图**原样**（不抠图）放**右下角小图**，画布比例按 logo 数量与形状自适应；
3. 在对话框**同时交付两个文件**：`原图名_puzzle.png`（透明底合成图）+ `原图名_puzzle.psd`（**分图层**：每张上传图独立一层——Original 衣服原图 / Logo-1、Logo-2… 每个印花各一层 / Text-1… 每个字符各一层 / Composite 合成预览）；
4. 两份文件同时归档到 `output/YYYYMMDD_HHMMSS/`（每批任务新建时间戳文件夹，互不覆盖）。

## 二、前置条件（硬性）

- 宿主 agent **必须具备多模态视觉识别能力**（看图判断"哪张是 logo、哪张是衣服"）与图像合成能力。本项目是操作指南 + 本地合成脚本（Pillow），**不内置识别引擎**。
- 本地软件依赖：Python 3.9+ 与 `Pillow`、`psd-tools`（合成与 PSD 兜底脚本用，见 `requirements.txt`）。
- 一键配置：`scripts/setup.ps1`（Windows PowerShell）。

## 三、必读清单（按任务类型）

| 场景 | 必读文件 |
|---|---|
| 接手项目 / 被询问项目 | `NAVIGATION.md`（顶层地图）→ 本文件（AGENTS.md） |
| 执行拼图任务 | `skill/SKILL.md`（完整流程）→ `config/skill.config.json`（布局/命名默认值） |
| 需要目录/路径/细节/排查 | `docs/PROJECT_MAP.md` |
| 人类阅读 | `README.md`（agent 可跳过） |

## 四、触发规则（重要）

- 用户**直接发送 2~4 张图片**（透明底 logo / 字符图 + 衣服原图）、且未给出其他明确任务 → **立即执行拼图工作流**，不要反问、不要等待额外指令。
- 用户发送图片并附带"拼图 / 拼一起 / 合成 / 做成展示图 / 印花排版"等文字 → 同样执行。
- **角色识别**：先用视觉判断哪张是衣服原图、哪些是 logo 组合件。判断依据（按优先级）：
  1. 图带背景/不透明（照片、白底、实拍）→ 大概率是衣服原图；
  2. 图是透明底（PNG 带 alpha、边缘有透明）→ 大概率是 logo；
  3. 内容有衣领/袖子/衣物轮廓、布料纹理 → 衣服；
  4. 内容是图案、文字、品牌标、卡通角色 → logo。
- **兜底**：若视觉判断**没有把握**（如衣服也是透明底、或衣服也是纯图案难以区分），**只问一句**："哪张是衣服原图？"（必要时可加"其余都按 logo 处理"），不展开其他问题。识别清楚后立即执行。
- 用户发送图片但明确要求其他操作（如"分析这张图""翻译图中文字"）→ 按用户要求执行，不触发拼图。
- 一次任务多个 logo：**2 个 logo 且无字符** → 两个 logo 50:50 排布；**1 个 logo + 1 张字符图** → 主 logo 在上、字符在下垂直堆叠；**1 个 logo 无字符** → 单图居中放置。

## 五、执行步骤（详见 `skill/SKILL.md`）

1. 存档：所有输入图原样保存到 `input/`（重名追加时间戳）；
2. 角色识别：视觉判断衣服图与 logo 组合件，不确定则兜底问一句；
3. 布局：读取 `config/skill.config.json` 的 `layout.*`，按参考图风格智能计算画布尺寸与各元素位置（复用 `skill/scripts/layout.py` 的逻辑口径）；
4. 合成 PNG：调用 `skill/scripts/compose_puzzle.py`（Pillow）生成透明底合成图；
5. 生成 PSD：优先 agent 原生 PSD 能力（**每张上传图独立一层**，层名规范：Original / Logo-1、Logo-2… / Text-1… / Composite）；否则运行 `python skill/scripts/build_psd.py`；
6. 交付：对话框同时交付 PNG + PSD；
7. 归档：`output/YYYYMMDD_HHMMSS/` 下放置各图 `原图名_puzzle.png` + `原图名_puzzle.psd`。

## 六、硬性规则（不得违反）

1. 每次任务**必须**同时交付 PNG + PSD 两份，不允许只给一张；
2. 每批任务**必须**在 `output/` 下新建独立时间戳文件夹，**不允许覆盖**已有产物；
3. 输入图**必须**留档到 `input/`；
4. **衣服图不抠图、不修饰**，发来什么样就贴什么样（位置/缩放除外）；logo 必须是透明底（用户自行扣好），若发现 logo 带白底/背景，**提示用户先去抠图项目处理**，不自动帮抠；
5. 除 logo 与衣服外，合成图背景**必须全透明**；
6. 产物（`input/`、`output/` 内容）不入 git 仓库（见 `.gitignore`），仓库只同步"项目本身"；
7. 执行窗口**禁止编写 / 修改任何脚本或项目文件**，只准调用项目现成脚本（`compose_puzzle.py` / `build_psd.py` / `layout.py`）与宿主自身能力；需要改动项目本体时，由项目所有者另行处理。

## 七、目录地图（速览，详见 `NAVIGATION.md` 与 `docs/PROJECT_MAP.md`）

```
拼图skill/
├── NAVIGATION.md            ← 顶层导航（全量目录树 + 任务索引，先读）
├── AGENTS.md                ← 本文件（行为手册）
├── README.md                ← 人类使用说明
├── .gitignore / .gitattributes / requirements.txt
├── config/skill.config.json ← 机器可读默认值（布局/触发/命名/路径）
├── docs/PROJECT_MAP.md      ← 项目地图与手册（详细）
├── skill/
│   ├── SKILL.md             ← 技能定义 + 完整执行流程
│   └── scripts/
│       ├── layout.py        ← 布局计算核心（共用）
│       ├── compose_puzzle.py← 合成：logo+字符+衣服 → 透明底 PNG
│       └── build_psd.py     ← PSD 兜底：分图层 PSD（每张上传图一层 + Composite）
├── scripts/setup.ps1        ← 一键配置
├── input/                   ← 输入留档
└── output/                  ← 产物归档（output/YYYYMMDD_HHMMSS/）
```

## 八、失败处理

- agent 无视觉识别/合成能力 → 明确告知"本技能需要宿主 agent 具备多模态视觉能力"，**不假装完成**。
- 合成或 PSD 生成失败 → 保留 `input/` 输入图，向用户说明失败环节与原因。
- 环境缺依赖（Pillow/psd-tools 未安装）→ 提示运行 `scripts/setup.ps1`。
- logo 非透明底 → 提示先去抠图项目处理，不自动帮抠（硬性规则 4）。
