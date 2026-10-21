#!/usr/bin/env python3
"""compose_puzzle.py — 服饰印花拼图合成脚本（Pillow，纯像素合成，无 AI 依赖）。

功能：把 1~2 张透明底 logo 图（可含 1~N 张字符图）+ 1 张衣服原图，
拼成一张透明底展示图（左侧 logo 组合大图 + 右下角衣服原图小图）。

用法：
  python compose_puzzle.py --logo logo1.png [--logo logo2.png] [--text text.png] \
      --garment garment.jpg --output out_puzzle.png [--config config/skill.config.json]

约定：
  - logo 必须透明底（带白底/背景时脚本会警告，但不自动抠图）；
  - 衣服原图不抠图、不修饰，原样等比缩放到右下角；
  - 画布比例智能自适应（复用 layout.py）。

依赖：Pillow（见 requirements.txt）。
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

from layout import compute_layout, load_config


def load_rgba(path: str, check_transparent: bool = False) -> Image.Image:
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
    if check_transparent:
        # 检查是否带不透明背景（仅 logo/字符图；衣服原图不检查，允许带背景）
        alpha = rgba.split()[-1]
        # histogram 第 0 项 = 全透明像素数
        hist = alpha.histogram()
        opaque = sum(hist[1:])
        total = max(alpha.width * alpha.height, 1)
        if opaque / total > 0.995:
            print(
                f"[warn] {Path(path).name} 几乎完全不透明（可能带背景），请确认是否为透明底 logo",
                file=sys.stderr,
            )
    return rgba


def paste_center(canvas: Image.Image, img: Image.Image, box) -> None:
    """把 img 等比缩放后居中贴到 box 内（不拉伸变形）。"""
    bx1, by1, bx2, by2 = box
    bw, bh = bx2 - bx1, by2 - by1
    scale = min(bw / img.width, bh / img.height)
    w = max(1, round(img.width * scale))
    h = max(1, round(img.height * scale))
    resized = img.resize((w, h), Image.LANCZOS)
    x = bx1 + (bw - w) // 2
    y = by1 + (bh - h) // 2
    canvas.alpha_composite(resized, (x, y))


def main() -> None:
    parser = argparse.ArgumentParser(description="logo + 字符 + 衣服 → 透明底拼图 PNG")
    parser.add_argument("--logo", action="append", required=True, help="透明底 logo 图（可多次传入，最多 2 张）")
    parser.add_argument("--text", action="append", default=[], help="字符图（可多次传入，置于 logo 下方）")
    parser.add_argument("--garment", required=True, help="衣服原图（不抠图，原样贴右下角）")
    parser.add_argument("--output", required=True, help="输出 PNG 路径")
    parser.add_argument("--config", default=None, help="config/skill.config.json 路径（可选）")
    args = parser.parse_args()

    if len(args.logo) > 2:
        parser.error("最多支持 2 张 logo 图")

    cfg = load_config(args.config)
    logos = [load_rgba(p, check_transparent=True) for p in args.logo]
    texts = [load_rgba(p, check_transparent=True) for p in args.text]
    garment = load_rgba(args.garment)

    layout = compute_layout(logos, texts, garment, cfg)
    W, H = layout["canvas"]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    for img, box in zip(logos, layout["logo_boxes"]):
        paste_center(canvas, img, box)
    for img, box in zip(texts, layout["text_boxes"]):
        paste_center(canvas, img, box)
    paste_center(canvas, garment, layout["garment_box"])

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")
    print(
        f"[ok] 拼图已生成: {out}（画布 {W}x{H}，"
        f"布局方向: {layout['direction']}，衣服框: {layout['garment_box']}）"
    )


if __name__ == "__main__":
    main()
