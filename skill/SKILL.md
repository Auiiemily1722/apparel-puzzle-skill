# SKILL.md — 服饰印花拼图技能（apparel-puzzle）

> 技能定义 + 完整执行流程。agent 执行拼图任务时读本文件。
> 布局默认值以 `config/skill.config.json` 为准；详细路径/命名见 `docs/PROJECT_MAP.md`。

---

## 1. 技能定位

**输入**：1~2 张透明底 logo 图（可含 1 张字符图）+ 1 张衣服原图。
**输出**：透明底合成展示图（PNG）+ 五层 PSD（Original / Cutout / Logo / Text / Composite）。
**风格**：参照"服饰印花设计展示图"——左侧 logo 组合大图，右下角衣服原图小图，背景全透明。

## 2. 触发与角色识别

- 触发：用户在对话窗直接发送图片（不说话）或附带拼图类关键词 → 立即执行。
- 角色识别（视觉判断，按优先级）：
  1. 带背景/不透明（照片、白底、实拍、有人穿着的衣物照）→ 衣服原图；
  2. 透明底 PNG（alpha 通道）→ logo；
  3. 衣领/袖子/布料纹理/衣物轮廓 → 衣服；
  4. 图案、品牌标、文字、卡通角色 → logo。
- 兜底：视觉判断没把握（如衣服也是透明底、衣服也是纯图案）→ **只问一句**："哪张是衣服原图？"识别清楚后继续。
- 特殊情况：**2 张 logo 且无字符** → 两 logo 50:50 排布；**1 logo + 1 字符** → 主 logo 在上、字符在下；**1 logo** → 单图。

## 3. 执行流程

### 3.1 存档（第 1 步）
所有输入图原样保存到 `input/`（保留原文件名；重名追加 `_YYYYMMDD_HHMMSS`）。

### 3.2 角色识别（第 2 步）
按第 2 节规则识别衣服图与 logo 组合件；不确定则兜底问一句。

### 3.3 布局计算（第 3 步）
布局逻辑与 `skill/scripts/layout.py` 口径一致，默认值读 `config/skill.config.json` 的 `layout.*`：

- **区域划分**：画布分为「左侧 logo 主区」与「右下角衣服区」。
  - 左侧 logo 主区：占画布高度约 `logo_zone_ratio`（默认 0.65），内容垂直居中；
  - 衣服区：占画布高度约 `garment_zone_ratio`（默认 0.22，浮动区间 `garment_ratio_min/max` 0.18~0.28）；
  - 四周留边距 `padding_ratio`（默认 0.05）。
- **左侧组合排布**（参照参考图：主 logo 在上、字符在下）：
  - **单 logo**：居中放置；
  - **1 logo + 1 字符**：主 logo 在上（占组合可用高度的约 70%）、字符在下（约 30%），间距 `logo_text_gap_ratio`；
  - **2 logo（50:50）**：两个 logo 面积对半，**排布方向按 logo 现状智能判断**——
    - 两 logo 均偏横向（宽>高）→ 上下堆叠（各占 50% 高度）；
    - 两 logo 均偏纵向或方形 → 左右并排（各占 50% 宽度）；
    - 一横一纵 → 以画布主区宽高比适配：主区偏宽则左右并排、偏高则上下堆叠。
- **画布自适应**（`smart_canvas: true`）：画布比例由 logo 组合与衣服的相对尺寸推导——
  1. 先按 logo 组合的宽高比 + 区域占比定出画布基准（宽、高）；
  2. 衣服按目标高度缩放到 `garment_zone_ratio` 区间，贴右下角，与右下边界留 `padding_ratio` 边距；
  3. 若 logo 组合横向很宽 → 画布偏横向（宽:高 ≈ 4:3 / 16:9 方向）；若组合纵向很高 → 画布偏纵向（3:4 / 9:16 方向）。具体由 `layout.py` 计算输出。

### 3.4 合成 PNG（第 4 步）
调用合成脚本（Pillow，不依赖宿主抠图/绘制能力，纯像素合成）：

```powershell
python skill/scripts/compose_puzzle.py `
  --logo input/logo1.png [--logo input/logo2.png] [--text input/text.png] `
  --garment input/garment.jpg --output output/xx_puzzle.png [--config config/skill.config.json]
```

- 画布 RGBA 全透明 → 左侧贴 logo 组合 → 右下角贴衣服原图（**不抠图**，保持原比例缩放到目标框）；
- 输出透明底 PNG，文件名 `原图名_puzzle.png`（衣服原图的文件名派生）。

### 3.5 生成 PSD（第 5 步）
优先 agent 原生 PSD 能力；否则运行兜底脚本：

```powershell
python skill/scripts/build_psd.py `
  --composite output/xx_puzzle.png --garment input/garment.jpg `
  --logo input/logo1.png [--logo input/logo2.png] [--text input/text.png] `
  --output output/xx_puzzle.psd [--config config/skill.config.json]
```

图层（自下而上，画布尺寸 = 合成图画布，层名英文避免编码问题）：

| 层 | 名称 | 内容 |
|---|---|---|
| 1 | Original | 衣服原图（贴在右下角对应位置的图层，原样） |
| 2 | Cutout | 衣服元素层（同位置的透明背景衣服图层，供手动编辑） |
| 3 | Logo | 主 logo 图层（左侧区域） |
| 4 | Text | 字符图层（左侧区域，无字符时可省略） |
| 5 | Composite | 合成结果（全部元素合并后的最终画面） |

### 3.6 交付与归档（第 6~7 步）
- 对话框**同时**交付 PNG + PSD；
- 归档到 `output/YYYYMMDD_HHMMSS/`（一批任务共用一个文件夹；同秒多批追加 `_1` `_2`）。

## 4. 命名规范

| 项 | 规则 | 示例 |
|---|---|---|
| 归档文件夹 | `YYYYMMDD_HHMMSS`（本地时间 24h） | `20261021_151000` |
| 合成 PNG | `衣服原图名_puzzle.png` | `tshirt_puzzle.png` |
| PSD | `衣服原图名_puzzle.psd` | `tshirt_puzzle.psd` |
| 输入留档 | 原名；重名追加时间戳 | `logo.png` / `logo_20261021_151000.png` |
| 同秒防重 | 文件夹名追加 `_1` `_2` | `20261021_151000_1` |

## 5. 硬性规则

1. PNG + PSD 成对交付；2. 每批独立时间戳文件夹不覆盖；3. 输入必存 `input/`；4. **衣服不抠图**、logo 必须透明底（带背景则提示先去抠图）；5. 合成图背景全透明；6. 产物不入 git；7. 执行窗口不改脚本不写项目文件。

## 6. 修改默认行为的入口

所有可调项集中在 `config/skill.config.json` 的 `layout.*`：
- `logo_zone_ratio` / `garment_zone_ratio` / `garment_ratio_min` / `garment_ratio_max`：左侧组合与右下角衣服的占画布比例；
- `padding_ratio` / `gap_ratio` / `logo_text_gap_ratio`：边距与间距；
- `two_logo_ratio`：两 logo 对半比例（0.5）；
- `smart_canvas`：画布比例自适应开关（`false` 时用固定基准比例）；
- `trigger.*`：触发与兜底提问开关。

改完配置无需重新安装，agent 每次执行都会重新读取。
