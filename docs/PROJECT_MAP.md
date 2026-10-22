# 项目地图与手册（PROJECT_MAP）

> 给 agent 和人类共用的详细手册。接手项目先读 `NAVIGATION.md`，执行任务读 `skill/SKILL.md`，本文件用于弄清每个路径是干什么的、布局规则、命名规范、故障排查与 git 同步。

## 1. 项目定位

**一句话**：用户在对话窗发透明底 logo 图（1~2 个，可带字符）+ 衣服原图 + 一串序列号 → agent 视觉识别角色、提取序列号 → 智能布局（左侧 logo 组合大图 + 右下角衣服原图小图）→ 交付透明底 PNG + 分图层 PSD（每张上传图独立一层，**以序列号命名**）→ 归档到 `output/`。

**三条铁律**：
1. 交付永远成对（PNG + PSD），不拆单；
2. 每批任务在 `output/` 下新建独立时间戳文件夹（一批图共用一个），不覆盖；
3. **衣服图不抠图**，原样贴入；logo 必须透明底。

## 2. 目录逐项说明

| 路径 | 类型 | 用途 | 谁读写 |
|---|---|---|---|
| `NAVIGATION.md` | 文档 | **最高层导航**：全量目录树 + 「任务→文件」索引，接手先读 | agent 必读 |
| `AGENTS.md` | 文档 | agent 行为手册：定位、触发规则、执行步骤、硬性规则 | agent 必读 |
| `README.md` | 文档 | 人类使用说明 | 人类 |
| `.gitignore` | 配置 | 产物/环境不入库 | git |
| `.gitattributes` | 配置 | LF 行尾统一，跨设备协作 | git |
| `requirements.txt` | 配置 | 依赖清单（psd-tools / Pillow） | setup.ps1 |
| `config/skill.config.json` | 配置 | **机器可读默认值**：布局比例、触发开关、命名、路径 | agent 执行时读 |
| `docs/PROJECT_MAP.md` | 文档 | 本文件 | agent/人类 |
| `skill/SKILL.md` | 技能 | 技能定义 + 完整执行流程（可被安装为运行时技能） | agent 执行时读 |
| `skill/scripts/layout.py` | 脚本 | 布局计算核心（画布/元素框），compose 与 PSD 共用 | agent 调用 |
| `skill/scripts/compose_puzzle.py` | 脚本 | 合成：logo+字符+衣服 → 透明底 PNG | agent 调用 |
| `skill/scripts/build_psd.py` | 脚本 | PSD 兜底：每张上传图独立一层（无合成预览层） | agent 调用 |
| `scripts/setup.ps1` | 脚本 | 一键配置：建目录、装依赖、可选安装技能 | 人类/agent 首次运行 |
| `input/` | 数据 | **输入素材留档**（logo/字符/衣服原图，原样保存） | agent 写入 |
| `output/` | 产物 | **生成结果归档**（每批任务一个时间戳子文件夹） | agent 写入 |

## 3. 一次完整任务的路径流（示例）

用户发送 `logo1.png`（透明底）+ `logo2.png`（透明底）+ `tshirt.jpg`（衣服原图）+ 序列号 `ABC123`，本地时间 2026-10-21 15:30:00：

```
用户对话框 ── logo1.png, logo2.png, tshirt.jpg + "ABC123"（不说话）
   │
   ▼（第1步 存档：原样存入 input/）
input/logo1.png, input/logo2.png, input/tshirt.jpg
   │
   ▼（第2步 视觉识别：带背景=衣服，透明底=logo；没把握只问一句）
   ▼（第3步 提取序列号：ABC123 → 作为产物文件名基础）
   ▼（第4步 布局：2 logo → 50:50 智能排布；画布自适应）
   │
   ▼（第5步 合成：compose_puzzle.py）
ABC123_puzzle.png（透明底：左侧双 logo + 右下角衣服）  ← 第5步
   │
   ▼（第6步 PSD：build_psd.py 兜底 或 agent 原生能力）
ABC123_puzzle.psd（分图层：每张上传图独立一层，无合成预览层）          ← 第6步
   │
   ├── 对话框交付：ABC123_puzzle.png + ABC123_puzzle.psd  ← 第7步
   └── output/20261021_153000/
          ├── ABC123_puzzle.png                          ← 第8步归档
          └── ABC123_puzzle.psd
```

同一秒多批任务 → `output/20261021_153000_1/`、`_2/`… 防重。

## 4. 布局规则（与 config/skill.config.json 对应）

| 场景 | 排布 | 参数 |
|---|---|---|
| 单 logo | 左侧居中 | `logo_zone_ratio`（占画布高 0.65） |
| 1 logo + 1 字符 | 主 logo 在上（70%）、字符在下（30%） | `logo_share_of_zone` / `text_share_of_zone` / `logo_text_gap_ratio` |
| 2 logo（无字符） | **50:50**：均横向→上下堆叠；其余→左右并排 | `two_logo_ratio`，方向由 `layout.py` 按 logo 现状判断 |
| 衣服 | 右下角小图，原样（不抠图）等比缩放 | `garment_zone_ratio`（0.22，浮动 0.18~0.28） |
| 边距 | 四周边距 | `padding_ratio`（0.05，按画布高度折算） |
| 画布比例 | **智能自适应**：由 logo 组合宽高比 + 衣服尺寸推导方向与比例，长边上限 2048px | `smart_canvas` |

**两 logo 排布方向判断规则**（`decide_two_logo_direction`）：
- 两 logo 均横向（宽≥高）→ **上下堆叠**（各占 50% 高度）；
- 一横一纵 / 均纵向 / 均方形 → **左右并排**（各占 50% 宽度）。

## 5. 命名规范（与 config/skill.config.json 对应）

| 项 | 规则 | 示例 |
|---|---|---|
| 归档文件夹 | `YYYYMMDD_HHMMSS`（本地时间 24h，无冒号） | `20261021_153000` |
| 合成 PNG | `序列号_puzzle.png`（无序列号回退衣服原图名） | `ABC123_puzzle.png` |
| PSD | `序列号_puzzle.psd`（无序列号回退衣服原图名） | `ABC123_puzzle.psd` |
| 输入留档 | 原名；重名追加时间戳 | `logo1.png` / `logo1_20261021_153000.png` |
| 同秒防重 | 文件夹名追加 `_1` `_2` | `20261021_153000_1` |

> 序列号：用户消息中的英文/数字串（如 `ABC123`、`KT-2024`）；若以图片形式发送（吊牌/标签截图），agent 用视觉识别读出。提取不到时回退衣服原图名。

## 6. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| agent 说"无法识别哪个是衣服" | 宿主 agent 无多模态视觉能力，或图实在难以区分 | 兜底只问一句"哪张是衣服原图？"；若 agent 无视觉能力 → 本项目不可用 |
| logo 带白底/背景 | 用户未先抠图 | 硬性规则 4：提示先去抠图项目处理，不自动帮抠 |
| 合成结果重叠/出界 | 极端形状输入 | 调 `config/skill.config.json` 的 `layout.*`（缩小 `garment_zone_ratio`、增大 `padding_ratio`）后重跑 |
| `compose_puzzle.py` 报 ModuleNotFoundError | 未装依赖 | 运行 `scripts/setup.ps1` |
| PSD 打不开 | 产物损坏/未走脚本 | 检查 `output/` 对应文件夹，重跑该任务 |
| 中文文件名乱码 | 终端编码 | PowerShell 用 `chcp 65001` 或 Windows Terminal |
| 画布比例不合预期 | 自适应结果不满意 | 关闭 `smart_canvas` 用固定基准，或直接改 `logo_zone_ratio` / `garment_zone_ratio` |
| 执行窗口 agent 想自己写脚本 / 改项目 | 未读 AGENTS.md 或偏离定位 | 明确告知：禁止编写或修改脚本，只准调用 `skill/scripts/` 现成脚本与宿主自身能力（AGENTS.md 硬性规则 7）；需要改动项目由所有者处理 |

## 7. git 与产物同步

- **默认**：`input/`、`output/` 被 `.gitignore` 忽略，仓库只同步项目本身（文档/技能/配置/脚本），体积小、clone 快。
- **双远程**：本项目默认同时推 GitHub 与 Gitee（仓库名 `apparel-puzzle-skill`）：
  ```powershell
  git remote add origin   https://github.com/<你的用户名>/apparel-puzzle-skill.git
  git remote add gitee    https://gitee.com/<你的用户名>/apparel-puzzle-skill.git
  git push origin main && git push gitee main
  ```
- **需要同步产物**（可选）：启用 git-lfs 后，把 `output/` 加入跟踪：
  ```powershell
  git lfs install
  git lfs track "output/**"
  git add .gitattributes output
  git commit -m "track outputs with lfs"
  ```

## 8. 修改默认行为的入口

所有可调项集中在 `config/skill.config.json`：
- `trigger.ask_when_uncertain`：`true`=视觉识别没把握时兜底问一句（默认）；`false`=按多数规则硬判；
- `trigger.keywords`：增减触发关键词；
- `output.*`：改文件夹/文件命名格式；
- `layout.*`：布局比例（见第 4 节）；
- `psd.layers` / `psd.layer_names`：增删/改名 PSD 图层。

改完配置无需重新安装，agent 每次执行都会重新读取。
