#!/usr/bin/env python3
"""layout.py — 服饰印花拼图布局计算核心（compose_puzzle.py 与 build_psd.py 共用）。

职责：根据 logo 组合（1~2 个 logo，可带字符图）+ 衣服原图，计算：
  - 画布尺寸（智能自适应比例）
  - 各元素在画布上的目标框 (x1, y1, x2, y2)

布局口径（与 skill/SKILL.md、config/skill.config.json 一致）：
  - 左侧 logo 主区占画布高度约 logo_zone_ratio（默认 0.65），内容垂直居中；
  - 右下角衣服区占画布高度约 garment_zone_ratio（默认 0.22，浮动 0.18~0.28）；
  - 四周边距 padding_ratio（默认 0.05，按画布高度折算）；
  - 单 logo：居中；1 logo + 字符：主 logo 在上（组合高 70%）、字符在下（30%）；
  - 2 logo：50:50，按 logo 现状智能排布（均横向→上下堆叠；其余→左右并排）。

用法（作为模块被脚本调用，不直接运行）：
  from layout import compute_layout, load_config
  result = compute_layout(logo_imgs, text_imgs, garment_img, cfg)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from PIL import Image

Box = Tuple[int, int, int, int]  # (x1, y1, x2, y2)

DEFAULT_CONFIG = {
    "layout": {
        "logo_zone_ratio": 0.65,
        "garment_zone_ratio": 0.22,
        "garment_ratio_min": 0.18,
        "garment_ratio_max": 0.28,
        "padding_ratio": 0.05,
        "gap_ratio": 0.04,
        "logo_text_gap_ratio": 0.06,
        "logo_share_of_zone": 0.7,
        "text_share_of_zone": 0.3,
        "two_logo_ratio": 0.5,
        "smart_canvas": True,
        "garment_anchor": "bottom_right",
    }
}

MAX_CANVAS = 2048  # 画布长边上限（像素）


def load_config(path: Optional[str] = None) -> dict:
    """读取 config/skill.config.json；缺失时返回内置默认值。"""
    cfg = DEFAULT_CONFIG.copy()
    if path and Path(path).is_file():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data.get("layout"), dict):
                cfg["layout"].update(data["layout"])
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[warn] 读取配置失败({exc})，使用内置默认值", file=sys.stderr)
    return cfg


def _size(img: Image.Image) -> Tuple[int, int]:
    return img.width, img.height


def _scale_to_height(img: Image.Image, target_h: int) -> Image.Image:
    if target_h <= 0:
        raise ValueError(f"目标高度必须为正数，收到 {target_h}")
    ratio = target_h / img.height
    target_w = max(1, round(img.width * ratio))
    return img.resize((target_w, target_h), Image.LANCZOS)


def _scale_to_width(img: Image.Image, target_w: int) -> Image.Image:
    if target_w <= 0:
        raise ValueError(f"目标宽度必须为正数，收到 {target_w}")
    ratio = target_w / img.width
    target_h = max(1, round(img.height * ratio))
    return img.resize((target_w, target_h), Image.LANCZOS)


def _fit_in_box(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """等比缩放到不超过 max_w × max_h 的框内。"""
    scale = min(max_w / img.width, max_h / img.height, 1.0)
    new_w = max(1, round(img.width * scale))
    new_h = max(1, round(img.height * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def decide_two_logo_direction(logo_imgs: Sequence[Image.Image]) -> str:
    """两 logo 的 50:50 排布方向：
    - 均横向（宽>=高）→ "vertical"（上下堆叠，各占 50% 高度）；
    - 其余（含一横一竖、均纵向/方形）→ "horizontal"（左右并排，各占 50% 宽度）。
    """
    if len(logo_imgs) < 2:
        return "single"
    both_landscape = all(img.width > img.height for img in logo_imgs)
    return "vertical" if both_landscape else "horizontal"


def _combo_natural(logo_imgs, text_imgs, cfg) -> Tuple[int, int, str]:
    """计算 logo 组合的自然尺寸（未缩放到画布前）与排布方向。"""
    layout = cfg["layout"]
    gap = max(1, round(cfg.get("max_h", 1024) * layout.get("logo_text_gap_ratio", 0.06))) if "max_h" in cfg else 8
    if len(logo_imgs) >= 2:
        direction = decide_two_logo_direction(logo_imgs)
        if direction == "vertical":
            # 上下堆叠：两 logo 缩放到相同目标高度 = 50% 组合高，宽度取各自等比
            # 先求组合宽高：两图都按"同一目标高"缩放后并排/堆叠
            # 简化：以两图自然高的和为组合高，宽取较宽者
            comb_w = max(img.width for img in logo_imgs)
            comb_h = sum(img.height for img in logo_imgs)
        else:
            comb_w = sum(img.width for img in logo_imgs)
            comb_h = max(img.height for img in logo_imgs)
    else:
        comb_w = logo_imgs[0].width
        comb_h = logo_imgs[0].height
    # 加上字符图（若有）：字符放主组合下方
    if text_imgs:
        comb_w = max(comb_w, max(t.width for t in text_imgs))
        comb_h = comb_h + gap + max(t.height for t in text_imgs)
    return comb_w, comb_h, direction if len(logo_imgs) >= 2 else "single"


def compute_layout(
    logo_imgs: Sequence[Image.Image],
    text_imgs: Sequence[Image.Image],
    garment_img: Image.Image,
    cfg: dict,
) -> dict:
    """计算布局。返回：
    {
      "canvas": (W, H),
      "logo_boxes": [(x1,y1,x2,y2), ...],   # 与 logo_imgs 一一对应
      "text_boxes": [(x1,y1,x2,y2), ...],   # 与 text_imgs 一一对应
      "garment_box": (x1,y1,x2,y2),
      "direction": "single"|"vertical"|"horizontal",
    }
    """
    layout = cfg["layout"]
    logo_zone = float(layout.get("logo_zone_ratio", 0.65))
    garment_zone = float(layout.get("garment_zone_ratio", 0.22))
    garment_min = float(layout.get("garment_ratio_min", 0.18))
    garment_max = float(layout.get("garment_ratio_max", 0.28))
    padding = float(layout.get("padding_ratio", 0.05))
    gap = float(layout.get("gap_ratio", 0.04))
    text_gap = float(layout.get("logo_text_gap_ratio", 0.06))
    logo_share = float(layout.get("logo_share_of_zone", 0.7))
    text_share = float(layout.get("text_share_of_zone", 0.3))

    if not logo_imgs or garment_img is None:
        raise ValueError("至少需要 1 张 logo 图与 1 张衣服图")

    comb_w, comb_h, direction = _combo_natural(logo_imgs, text_imgs, cfg)

    # 画布高：让组合占 logo_zone 比例（组合自然大小直接放，不缩放）
    canvas_h = max(1, round(comb_h / logo_zone))
    pad_px = round(canvas_h * padding)

    # 画布宽：左侧组合区 + 衣服区 的较大者，含边距
    canvas_w = max(
        comb_w + pad_px * 2 + round(canvas_h * gap),   # 组合宽 + 左右边距 + 间隙
        round(garment_img.width / max(garment_img.height, 1) * canvas_h * garment_zone)
        + pad_px * 2,
    )

    # 画布长边上限约束：整体缩放
    long_edge = max(canvas_w, canvas_h)
    if long_edge > MAX_CANVAS:
        scale = MAX_CANVAS / long_edge
        canvas_w = max(1, round(canvas_w * scale))
        canvas_h = max(1, round(canvas_h * scale))
        pad_px = max(1, round(pad_px * scale))

    # ---- 左侧组合排布 ----
    logo_boxes: List[Box] = []
    text_boxes: List[Box] = []

    combo_zone_top = pad_px
    combo_zone_bottom = canvas_h - pad_px
    combo_zone_h = combo_zone_bottom - combo_zone_top
    combo_zone_w = canvas_w - pad_px * 2

    # 可用高度 = 组合区（占 logo_zone 比例部分），字符占 text_share
    logo_zone_px = round(canvas_h * logo_zone)
    text_zone_px = max(1, round(logo_zone_px * text_share / max(logo_share, 1e-6)))
    logo_zone_px = max(1, logo_zone_px - text_zone_px - round(logo_zone_px * text_gap))

    if len(logo_imgs) >= 2 and direction != "single":
        if direction == "vertical":
            # 上下堆叠 50:50：两 logo 同高
            half_h = logo_zone_px // 2
            y_cursor = combo_zone_top + (combo_zone_h - logo_zone_px) // 2
            for img in logo_imgs:
                fit = _scale_to_height(img, half_h)
                x1 = pad_px + (combo_zone_w - fit.width) // 2
                logo_boxes.append((x1, y_cursor, x1 + fit.width, y_cursor + fit.height))
                y_cursor += fit.height
        else:
            # 左右并排 50:50：两 logo 同宽（占组合区宽一半）
            half_w = combo_zone_w // 2
            y_cursor = combo_zone_top + (combo_zone_h - logo_zone_px) // 2
            x_cursor = pad_px
            for img in logo_imgs:
                fit = _scale_to_width(img, half_w)
                if fit.height > logo_zone_px:  # 防止过高溢出
                    fit = _scale_to_height(fit, logo_zone_px)
                logo_boxes.append((x_cursor, y_cursor, x_cursor + fit.width, y_cursor + fit.height))
                x_cursor += half_w
    else:
        # 单 logo（或主 logo）：占组合区 logo_share 高度，水平居中
        target_h = logo_zone_px
        fit = _fit_in_box(logo_imgs[0], combo_zone_w, target_h)
        x1 = pad_px + (combo_zone_w - fit.width) // 2
        y1 = combo_zone_top + (combo_zone_h - logo_zone_px) // 2
        logo_boxes.append((x1, y1, x1 + fit.width, y1 + fit.height))

    # 字符图：主组合下方
    if text_imgs:
        text_top = max(b[3] for b in logo_boxes) + round(logo_zone_px * text_gap)
        text_zone_bottom = combo_zone_bottom
        for t in text_imgs:
            avail_h = max(1, text_zone_bottom - text_top)
            avail_w = combo_zone_w
            fit = _fit_in_box(t, avail_w, avail_h)
            x1 = pad_px + (avail_w - fit.width) // 2
            text_boxes.append((x1, text_top, x1 + fit.width, text_top + fit.height))
            text_top += fit.height + max(1, round(avail_h * text_gap * 0.5))

    # ---- 右下角衣服区 ----
    # 目标高度在 garment_zone 区间内浮动：优先 garment_zone，若组合过高导致重叠则收缩
    g_target_h = max(1, round(canvas_h * garment_zone))
    g_fit = _fit_in_box(garment_img, canvas_w - pad_px * 2, g_target_h)
    # 重叠规避：衣服左上角不得侵入组合区域（所有左侧元素右缘的最大值 + 间隙）
    all_left_boxes = list(logo_boxes) + list(text_boxes)
    left_right_edge = max(b[2] for b in all_left_boxes) if all_left_boxes else pad_px
    min_g_x = left_right_edge + round(canvas_h * gap)
    g_x = canvas_w - pad_px - g_fit.width
    if g_x < min_g_x:
        # 太挤：缩小衣服到 garment_min 高度区间，仍不够则扩展画布
        shrink = min(
            (min_g_x - g_x + g_fit.width) / max(g_fit.width, 1),
            garment_zone / max(garment_min, 1e-6),
        )
        if shrink > 1:
            g_fit = _fit_in_box(garment_img, canvas_w - pad_px * 2, max(1, round(g_target_h / shrink)))
        g_x = canvas_w - pad_px - g_fit.width
        if g_x < min_g_x:  # 仍重叠：扩展画布宽
            extra = min_g_x - g_x
            canvas_w += extra
            g_x = min_g_x
    g_y = canvas_h - pad_px - g_fit.height
    garment_box = (g_x, g_y, g_x + g_fit.width, g_y + g_fit.height)

    return {
        "canvas": (canvas_w, canvas_h),
        "logo_boxes": logo_boxes,
        "text_boxes": text_boxes,
        "garment_box": garment_box,
        "direction": direction,
    }
