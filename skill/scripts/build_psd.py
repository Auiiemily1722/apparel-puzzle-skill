#!/usr/bin/env python3
"""build_psd.py — 服饰印花拼图 PSD 兜底脚本（psd-tools，五层）。

图层结构（自下而上，层名英文避免 PSD 名称编码问题，画布=合成图画布）：
  1. Original  （衣服原图：右下角对应位置的图层，原样）
  2. Logo-1    （第 1 张 logo 图层：左侧区域；每张 logo 独立一层，Logo-2…）
  3. Text-1    （第 1 张字符图图层：左侧区域；每张字符图独立一层，Text-2…，无字符时省略）

层数 = 上传图数：每个印花 / 字符 / 衣服各占一层，无合成预览层。

用法：
  python build_psd.py --garment garment.jpg --logo logo1.png [--logo logo2.png] \
      [--text text.png] --output out.psd [--config config/skill.config.json]

依赖：psd-tools + Pillow（见 requirements.txt）。
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
except ImportError as exc:  # pragma: no cover
    sys.exit(f"[X] 缺少依赖：{exc}\n    请先运行 scripts/setup.ps1 或 pip install -r requirements.txt")

from layout import compute_layout, load_config, trim_inputs


def load_rgba(path: str) -> Image.Image:
    with Image.open(path) as img:
        return img.convert("RGBA")


def paste_center(canvas: Image.Image, img: Image.Image, box) -> None:
    """把 img 等比缩放后居中贴到 box 内（与 compose_puzzle.py 口径一致）。"""
    bx1, by1, bx2, by2 = box
    bw, bh = bx2 - bx1, by2 - by1
    scale = min(bw / img.width, bh / img.height)
    w = max(1, round(img.width * scale))
    h = max(1, round(img.height * scale))
    resized = img.resize((w, h), Image.LANCZOS)
    x = bx1 + (bw - w) // 2
    y = by1 + (bh - h) // 2
    canvas.alpha_composite(resized, (x, y))


def build_layer(size, paste_specs, name: str) -> Image.Image:
    """按 paste_specs（(img, box) 列表）构建单层画布。"""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    for img, box in paste_specs:
        paste_center(canvas, img, box)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="logo + 字符 + 衣服 → 五层 PSD")
    parser.add_argument("--garment", required=True, help="衣服原图路径")
    parser.add_argument("--logo", action="append", required=True, help="透明底 logo 图（可多次，最多 2 张）")
    parser.add_argument("--text", action="append", default=[], help="字符图（可多次）")
    parser.add_argument("--output", required=True, help="输出 PSD 路径")
    parser.add_argument("--config", default=None, help="config/skill.config.json 路径（可选）")
    args = parser.parse_args()

    if len(args.logo) > 2:
        parser.error("最多支持 2 张 logo 图")

    cfg = load_config(args.config)
    # 裁剪 logo/字符图的透明留白（衣服原图不裁剪，原样贴入）
    logos = trim_inputs([load_rgba(p) for p in args.logo])
    texts = trim_inputs([load_rgba(p) for p in args.text])
    garment = load_rgba(args.garment)

    layout = compute_layout(logos, texts, garment, cfg)
    size = layout["canvas"]
    W, H = size

    garment_box = layout["garment_box"]
    logo_pastes = list(zip(logos, layout["logo_boxes"]))
    text_pastes = list(zip(texts, layout["text_boxes"]))

    layers: list = []
    # 每张上传图独立一层（用户可单独编辑每个印花/字符/衣服；无合成预览层）：
    layers.append(("Original", [(garment, garment_box)]))      # 1. 衣服原图（独立层）
    for i, paste in enumerate(logo_pastes, 1):                 # 2+. 每个 logo 独立一层
        layers.append((f"Logo-{i}", [paste]))
    for i, paste in enumerate(text_pastes, 1):                 # 每个字符图独立一层
        layers.append((f"Text-{i}", [paste]))

    psd = PSDImage.new("RGBA", size)
    for name, pastes in layers:
        layer_img = build_layer(size, pastes, name)
        psd.append(PixelLayer.frompil(layer_img, psd, name))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    psd.save(str(out))
    names = [n for n, _ in layers]
    print(f"[ok] PSD 已生成: {out}（画布 {W}x{H}，{len(names)} 层: {' / '.join(names)}）")


if __name__ == "__main__":
    main()
