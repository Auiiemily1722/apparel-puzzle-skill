# NAVIGATION.md — 项目导航（最高层入口）

> **任何 agent / 任何人接手本项目，先读本文件。**
> 本文件是整个仓库的"顶层地图"：完整目录树 + 「任务 → 读哪个文件」索引。
> 读完本文件即可按需跳读对应文件，**不需要通读整个仓库**。

---

## 1. 这个项目一句话

**服饰印花设计展示图拼接技能（apparel-puzzle-skill）**：多模态 agent 收到用户直接发送的 **透明底 logo 图（1~2 个，可附带字符图）+ 衣服原图** 后，自动识别角色 → 把 logo 组合（左侧大图）+ 衣服原图（右下角小图，不抠图、原样贴入）拼成一张**透明底展示图**，同时交付 **PNG + PSD**。

## 2. 全量目录树

```
拼图skill/                          ← git 仓库根（双远程：GitHub + Gitee，仓库名 apparel-puzzle-skill）
│
├── NAVIGATION.md                   ← 本文件（最高层导航，先读我）
├── AGENTS.md                       ← agent 行为手册（定位/触发规则/执行步骤/硬性规则）
├── README.md                       ← 人类使用说明（agent 可跳过）
├── .gitignore                      ← 产物/环境不入库
├── .gitattributes                  ← LF 行尾统一（跨设备）
├── requirements.txt                ← Python 依赖（psd-tools / Pillow）
│
├── config/                         ← 机器可读默认值
│   └── skill.config.json           ←   布局比例/触发开关/命名规范/路径（agent 执行时读）
│
├── docs/                           ← 文档
│   └── PROJECT_MAP.md              ←   项目地图与手册（详细，含布局规则/故障排查/git 说明）
│
├── skill/                          ← 技能本体（可整体安装到 agent 技能根目录）
│   ├── SKILL.md                    ←   技能定义 + 完整执行流程（agent 执行时读）
│   └── scripts/
│       ├── layout.py               ←   布局计算核心（画布尺寸/元素定位，compose 与 PSD 共用）
│       ├── compose_puzzle.py       ←   合成脚本：logo+字符+衣服 → 透明底 PNG
│       └── build_psd.py            ←   PSD 兜底脚本：五层（Original/Cutout/Logo/Text/Composite）
│
├── scripts/
│   └── setup.ps1                   ← 一键配置（建目录/装依赖/可选安装技能）
│
├── input/                          ← 输入素材留档（原图不入 git）
│   └── .gitkeep
└── output/                         ← 产物归档（output/YYYYMMDD_HHMMSS/，不入 git）
    └── .gitkeep
```

## 3. 「任务 → 读哪个文件」索引

| 我想做什么 | 去读 |
|---|---|
| 接手项目 / 被问"这项目干什么" | **本文件（NAVIGATION.md）→ AGENTS.md** |
| 执行一次拼图任务（完整流程） | `skill/SKILL.md` → `config/skill.config.json` |
| 弄清某路径/命名/产物放哪 | `docs/PROJECT_MAP.md` |
| 调布局（logo 占比/衣服大小/画布方向） | `config/skill.config.json` 的 `layout.*` |
| 排查合成/PSD 失败、环境问题 | `docs/PROJECT_MAP.md` 第 6 节故障排查 |
| 人类快速上手（不写代码） | `README.md` |
| 装环境/重装依赖 | `scripts/setup.ps1` |
| 看合成脚本如何算位置 | `skill/scripts/layout.py` |
| 改脚本行为 | 先读 `skill/SKILL.md` → 对应脚本，**改动项目本体需项目所有者处理** |

## 4. 快速开始（新设备，约 1 分钟）

```powershell
git clone <远程地址>              # GitHub 或 Gitee 任一地址
cd apparel-puzzle-skill
.\scripts\setup.ps1              # 建目录 + 装依赖（Python 3.9+）
```

然后：让多模态 agent 打开本项目文件夹，**直接发送透明底 logo 图（可多张）+ 衣服原图，不说话**，agent 自动拼图并交付 PNG + PSD。

## 5. 三条铁律（详见 AGENTS.md）

1. 交付永远成对：**PNG + PSD**，不拆单；
2. 每批任务在 `output/` 下新建独立时间戳文件夹，不覆盖；
3. **衣服图不抠图**，发来什么样就贴什么样；logo 必须是透明底（用户自行扣好）。
