#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/typeset_card_gen.py
排版卡三剑客离线渲染引擎 (Typeset Card Offline Rasterizer)

职责：
  接收 JSON 数据与卡片类型（quote / contrast / checklist），
  安全注入 HTML 模板，调用本地无头 Google Chrome 渲染为 2160 宽高清 Retina PNG (支持自适应高度)。
  纯本地离线执行，0 API 消耗，中间组装 HTML 严格收敛在 generated/tmp/，渲染后立即销毁。
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# PIL 软导入保护
try:
    from PIL import Image
except ImportError:
    Image = None

# 常量与路径定义
REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "assets" / "typeset-card"
TMP_DIR = REPO_ROOT / "generated" / "tmp"

SUPPORTED_TYPES = ("quote", "contrast", "checklist")


def find_chrome() -> str:
    """寻找本地 Google Chrome / Chromium 可执行文件路径。"""
    # 1. 优先从环境变量读取
    env_chrome = os.getenv("CHROME_BIN") or os.getenv("GOOGLE_CHROME_BIN")
    if env_chrome and os.path.isfile(env_chrome) and os.access(env_chrome, os.X_OK):
        return env_chrome

    # 2. PATH 探测
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path

    # 3. 常见绝对路径探测
    candidates = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c

    raise FileNotFoundError(
        "未在系统中找到可用的 Google Chrome 或 Chromium 可执行文件，"
        "请确保已安装并在 PATH 中，或配置 CHROME_BIN 环境变量。"
    )


def safe_escape(val: Any) -> str:
    """对用户输入进行安全 HTML 转义，并转换换行符为 <br/>。"""
    if val is None:
        return ""
    text = str(val)
    escaped = html.escape(text)
    return escaped.replace("\r\n", "<br/>").replace("\n", "<br/>")


def apply_accent_highlight(text: str, accent_word: Optional[str]) -> str:
    """若指定了强调词，且出现在文本中，则将首次出现的强调词包裹在 <span class="em"> 中。"""
    if not accent_word or not text:
        return text
    escaped_accent = html.escape(accent_word)
    if escaped_accent in text:
        return text.replace(escaped_accent, f'<span class="em">{escaped_accent}</span>', 1)
    return text


def build_quote_html(template: str, data: Dict[str, Any]) -> str:
    """组装金句卡 HTML。"""
    kicker = safe_escape(data.get("kicker", "QUOTE // 核心洞察"))
    raw_quote = str(data.get("quote", ""))
    accent = data.get("accent_word") or data.get("highlight_phrase")
    
    escaped_quote = safe_escape(raw_quote)
    highlighted_quote = apply_accent_highlight(escaped_quote, accent)

    # 字数自适应：字数超过 40 字时应用 long-text 类安全缩小字号
    quote_class = "long-text" if len(raw_quote) > 40 else ""

    author = safe_escape(data.get("author", "数效笔记 · 数小二 // 踩坑实录"))
    footer_right = safe_escape(data.get("footer_right", data.get("source", "")))

    html_out = template
    html_out = html_out.replace("{{KICKER}}", kicker)
    html_out = html_out.replace("{{QUOTE}}", highlighted_quote)
    html_out = html_out.replace("{{QUOTE_CLASS}}", quote_class)
    html_out = html_out.replace("{{AUTHOR}}", author)
    html_out = html_out.replace("{{FOOTER_RIGHT}}", footer_right)
    return html_out


# 要点关键词与骨架词高精度匹配正则 (中英文方括号、六角括号、全半角冒号)
TAG_PATTERN = re.compile(r'^\s*(?:\[|【|［)([^\]】］]{2,8})(?:\]|】|］)\s*(.+)$')
COLON_PATTERN = re.compile(r'^\s*([^：:\s]{2,8})[：:]\s*(.+)$')


def format_contrast_point(p: Any, bullet_cls: str, bullet_char: str) -> str:
    """格式化单条对比要点，支持骨架词标签提炼与传统文本优雅降级。"""
    if isinstance(p, dict):
        tag = p.get("tag") or p.get("title")
        body = p.get("desc") or p.get("text") or ""
        if tag:
            return (
                f'<div class="point-item"><span class="point-bullet {bullet_cls}">{bullet_char}</span>'
                f'<span class="point-badge">[{safe_escape(str(tag).strip())}]</span>'
                f'<span class="point-text">{safe_escape(str(body).strip())}</span></div>'
            )
        return (
            f'<div class="point-item"><span class="point-bullet {bullet_cls}">{bullet_char}</span>'
            f'<span class="point-text">{safe_escape(str(body))}</span></div>'
        )

    if isinstance(p, str):
        p_str = p.strip()
        m_tag = TAG_PATTERN.match(p_str)
        if m_tag:
            tag = m_tag.group(1).strip()
            body = m_tag.group(2).strip()
            return (
                f'<div class="point-item"><span class="point-bullet {bullet_cls}">{bullet_char}</span>'
                f'<span class="point-badge">[{safe_escape(tag)}]</span>'
                f'<span class="point-text">{safe_escape(body)}</span></div>'
            )
        m_colon = COLON_PATTERN.match(p_str)
        if m_colon:
            tag = m_colon.group(1).strip()
            body = m_colon.group(2).strip()
            return (
                f'<div class="point-item"><span class="point-bullet {bullet_cls}">{bullet_char}</span>'
                f'<span class="point-badge">[{safe_escape(tag)}]</span>'
                f'<span class="point-text">{safe_escape(body)}</span></div>'
            )
        return (
            f'<div class="point-item"><span class="point-bullet {bullet_cls}">{bullet_char}</span>'
            f'<span class="point-text">{safe_escape(p)}</span></div>'
        )

    return (
        f'<div class="point-item"><span class="point-bullet {bullet_cls}">{bullet_char}</span>'
        f'<span class="point-text">{safe_escape(str(p))}</span></div>'
    )


def build_contrast_html(template: str, data: Dict[str, Any]) -> str:
    """组装对比卡 HTML。"""
    kicker = safe_escape(data.get("kicker", "PARADIGM SHIFT // 认知对撞"))

    # 标题组装
    title_line1 = data.get("title_line1")
    title_highlight = data.get("title_highlight")
    if title_line1 and title_highlight:
        title = f"{safe_escape(title_line1)}<br/><span class=\"em\">{safe_escape(title_highlight)}</span>"
    else:
        raw_title = str(data.get("title", "别做甩手掌柜 把它当结对搭子"))
        title = apply_accent_highlight(safe_escape(raw_title), data.get("accent_word"))

    # 上方卡片 (误区/旧模式)
    left_title = safe_escape(data.get("bad_title") or data.get("left_title") or "✕ 常见误区")
    left_content_html = ""
    # 优先 points 列表，其次 desc 文本
    left_points = data.get("left_points") or (data.get("left", {}).get("points") if isinstance(data.get("left"), dict) else None)
    if left_points and isinstance(left_points, list):
        items_html = [
            format_contrast_point(p, "bullet-bad", "✕")
            for p in left_points
        ]
        left_content_html = "\n".join(items_html)
    else:
        bad_desc = data.get("bad_desc") or data.get("left_desc") or (data.get("left", {}).get("desc") if isinstance(data.get("left"), dict) else "")
        left_content_html = f'<div class="point-desc">{safe_escape(bad_desc)}</div>'

    # 下方卡片 (正解/新解法)
    right_title = safe_escape(data.get("good_title") or data.get("right_title") or "✓ 高手正解")
    right_content_html = ""
    right_points = data.get("right_points") or (data.get("right", {}).get("points") if isinstance(data.get("right"), dict) else None)
    if right_points and isinstance(right_points, list):
        items_html = [
            format_contrast_point(p, "bullet-good", "✓")
            for p in right_points
        ]
        right_content_html = "\n".join(items_html)
    else:
        good_desc = data.get("good_desc") or data.get("right_desc") or (data.get("right", {}).get("desc") if isinstance(data.get("right"), dict) else "")
        right_content_html = f'<div class="point-desc">{safe_escape(good_desc)}</div>'

    # 底部结论胶囊
    conclusion_text = data.get("conclusion") or data.get("takeaway") or data.get("pill") or "小步快跑，阶段验证"
    conclusion = safe_escape(conclusion_text)

    footer_left = safe_escape(data.get("footer_left") or data.get("author") or "数效笔记 · 数小二 原创复盘")
    footer_right = safe_escape(data.get("footer_right", data.get("source", "LESS IS MORE // VERIFY FAST")))

    html_out = template
    html_out = html_out.replace("{{KICKER}}", kicker)
    html_out = html_out.replace("{{TITLE}}", title)
    html_out = html_out.replace("{{LEFT_TITLE}}", left_title)
    html_out = html_out.replace("{{LEFT_CONTENT}}", left_content_html)
    html_out = html_out.replace("{{RIGHT_TITLE}}", right_title)
    html_out = html_out.replace("{{RIGHT_CONTENT}}", right_content_html)
    html_out = html_out.replace("{{CONCLUSION}}", conclusion)
    html_out = html_out.replace("{{FOOTER_LEFT}}", footer_left)
    html_out = html_out.replace("{{AUTHOR}}", footer_left)
    html_out = html_out.replace("{{FOOTER_RIGHT}}", footer_right)
    return html_out


def build_checklist_html(template: str, data: Dict[str, Any]) -> str:
    """组装实操清单卡 HTML。"""
    kicker = safe_escape(data.get("kicker", "PRACTICAL CHECKLIST // 实操避坑指南"))
    tag = safe_escape(data.get("tag", "实操小抄"))

    # 标题组装
    title_line1 = data.get("title_line1")
    title_highlight = data.get("title_highlight")
    if title_line1 and title_highlight:
        title = f"{safe_escape(title_line1)}<br/><span class=\"em\">{safe_escape(title_highlight)}</span>"
    else:
        raw_title = str(data.get("title", "日常高效用 AI 的 3 个保命习惯"))
        title = apply_accent_highlight(safe_escape(raw_title), data.get("accent_word"))

    # 清单项组装 (3~4 项)
    items_raw = data.get("items", [])
    rendered_items = []
    for i, it in enumerate(items_raw, start=1):
        idx = safe_escape(it.get("idx") or f"{i:02d}")
        it_title = safe_escape(it.get("title", f"清单要点 {i}"))
        it_desc = safe_escape(it.get("desc", ""))
        rendered_items.append(
            f'      <div class="check-item">\n'
            f'        <div class="check-badge">{idx}</div>\n'
            f'        <div class="check-content">\n'
            f'          <div class="check-title">{it_title}</div>\n'
            f'          <div class="check-desc">{it_desc}</div>\n'
            f'        </div>\n'
            f'      </div>'
        )

    items_html = "\n".join(rendered_items) if rendered_items else "<!-- 无清单项 -->"

    footer_left = safe_escape(data.get("footer_left", "数效笔记 · 数小二 独家整理"))
    footer_right = safe_escape(data.get("footer_right", "CONTEXT > PROMPT MAGIC"))

    html_out = template
    html_out = html_out.replace("{{KICKER}}", kicker)
    html_out = html_out.replace("{{TAG}}", tag)
    html_out = html_out.replace("{{TITLE}}", title)
    html_out = html_out.replace("{{ITEMS}}", items_html)
    html_out = html_out.replace("{{FOOTER_LEFT}}", footer_left)
    html_out = html_out.replace("{{FOOTER_RIGHT}}", footer_right)
    return html_out


def render_card(
    card_type: str,
    data: Dict[str, Any],
    output_png: Union[str, Path],
    timeout: int = 30,
) -> str:
    """核心渲染函数：渲染单张卡片到指定 PNG 路径。

    Args:
        card_type: 'quote', 'contrast' 或 'checklist'
        data: 卡片数据字典
        output_png: 输出 PNG 绝对或相对路径
        timeout: Chrome 截图超时时间 (秒)，默认 30

    Returns:
        output_png 的字符串绝对路径
    """
    card_type = card_type.lower().strip()
    if card_type not in SUPPORTED_TYPES:
        raise ValueError(f"不支持的卡片类型: '{card_type}'，仅支持: {SUPPORTED_TYPES}")

    template_file = TEMPLATES_DIR / f"{card_type}.html"
    if not template_file.is_file():
        raise FileNotFoundError(f"未找到模板文件: {template_file}")

    template_content = template_file.read_text(encoding="utf-8")

    # 根据类型组装 HTML 内容
    if card_type == "quote":
        rendered_html = build_quote_html(template_content, data)
    elif card_type == "contrast":
        rendered_html = build_contrast_html(template_content, data)
    elif card_type == "checklist":
        rendered_html = build_checklist_html(template_content, data)
    else:
        raise ValueError(f"未知卡片类型: {card_type}")

    # 准备沙箱临时目录
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_filename = f"tmp_card_{card_type}_{uuid.uuid4().hex[:8]}.html"
    tmp_html_path = TMP_DIR / tmp_filename

    out_path = Path(output_png).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chrome_bin = find_chrome()

    try:
        # 1. 写入中间组装 HTML 到沙箱目录
        tmp_html_path.write_text(rendered_html, encoding="utf-8")

        # 2. 调用 Chrome 进行 2x 无头离线渲染
        # 注意：
        # - quote 与 contrast 卡支持自适应动态高度，配合透明底画布在 PIL 阶段精准按内容边界裁剪；
        #   设定 1080,3600 充裕的虚拟安全缓冲区，消除长内容截断隐患。
        # - checklist 卡等固定为 4:5 规格。Linux 无头 Chrome (--headless=new) 启动时分配 87px
        #   窗口外壳装饰偏移，故传入 1080,1437 (1350 + 87) 确保内部视口严格达到 1350px。
        is_dynamic_height = card_type in ("quote", "contrast")
        window_size = "1080,3600" if is_dynamic_height else "1080,1437"

        cmd = [
            chrome_bin,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--force-device-scale-factor=2",
            f"--window-size={window_size}",
            "--default-background-color=00000000",
            f"--screenshot={out_path}",
            f"file://{tmp_html_path.resolve()}",
        ]

        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Chrome 无头渲染失败 (退出码 {result.returncode}):\n{result.stderr}"
            )

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise RuntimeError(f"渲染产物不存在或为空: {out_path}")

        # 3. PIL 图像尺寸精确对齐与体积优化 (软依赖)
        if Image is not None:
            try:
                with Image.open(out_path) as im:
                    if is_dynamic_height:
                        # 金句卡与对比卡自适应高度：根据卡片内容动态计算高度，消除上下多余大面积留白
                        # 通过 alpha 通道 getbbox 获取实际渲染内容高度并精准裁剪
                        bbox = im.getbbox()
                        if bbox:
                            im = im.crop((0, 0, 2160, bbox[3]))
                    else:
                        # 清单卡等固定为标准 4:5 固定规格 (2160x2700)
                        # Linux 无头 Chrome (--headless=new) 会在窗口高度中预留 87px 作为窗口栏/标题装饰区域，
                        # 导致 --window-size=1080,1350 时实际网页视口缩水为 1080x1263，底部 87px 被截断并残留白条。
                        # 为确保网页真实视口严格等于 1080x1350，我们传入窗口高度 1437 (1350 + 87)，
                        # 在 2x 缩放下渲染出 2160x2874 的截图缓冲区，前 2160x2700 即为完整的 1080x1350 网页正文。
                        # 此处裁剪多余的底部区域，确保最终输出严格为 2160x2700，0白条且底部署名完整可见。
                        if im.size[0] == 2160 and im.size[1] > 2700:
                            im = im.crop((0, 0, 2160, 2700))
                    im.save(out_path, "PNG", optimize=True)
            except Exception as e:
                # 优化失败不中断流程，保留 Chrome 原生截图
                print(f"[Warning] PIL 图像处理跳过: {e}", file=sys.stderr)

        return str(out_path)

    finally:
        # 4. 临时文件生命周期闭环：必须彻底清理中间组装 HTML
        if tmp_html_path.exists():
            try:
                tmp_html_path.unlink()
            except OSError:
                pass


def render_cards_from_file(
    json_file: Union[str, Path],
    output_dir: Union[str, Path],
    timeout: int = 30,
) -> List[Path]:
    """从卡片数据 JSON 文件批量渲染卡片。

    Args:
        json_file: 包含卡片数据的 JSON 文件路径
        output_dir: 产物图片输出目录
        timeout: 超时时间 (秒)

    Returns:
        生成的卡片 PNG 路径列表
    """
    json_path = Path(json_file).resolve()
    if not json_path.is_file():
        raise FileNotFoundError(f"未找到卡片数据文件: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 规范化数据为列表
    cards: List[Dict[str, Any]] = []
    if isinstance(raw_data, list):
        cards = raw_data
    elif isinstance(raw_data, dict):
        if "cards" in raw_data and isinstance(raw_data["cards"], list):
            cards = raw_data["cards"]
        elif any(k.startswith("card_") for k in raw_data.keys()):
            for k in sorted(raw_data.keys()):
                if k.startswith("card_") and isinstance(raw_data[k], dict):
                    cards.append(raw_data[k])
        elif "type" in raw_data:
            cards = [raw_data]
        else:
            raise ValueError(f"无法识别的卡片数据格式: {json_path}")
    else:
        raise ValueError(f"JSON 顶层必须为 dict 或 list: {json_path}")

    out_dir_path = Path(output_dir).resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    generated_paths: List[Path] = []
    for idx, card_dict in enumerate(cards, start=1):
        card_type = card_dict.get("type")
        if not card_type:
            # 默认兜底策略：第一张为 quote，第二张为 contrast
            card_type = "quote" if idx == 1 else "contrast"

        out_name = card_dict.get("filename") or f"card_{idx:02d}.png"
        target_png = out_dir_path / out_name

        rendered_str = render_card(card_type, card_dict, target_png, timeout=timeout)
        generated_paths.append(Path(rendered_str))

    return generated_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Typeset Card 离线渲染器 — 将数据和 HTML 模板光栅化为高清卡片 PNG"
    )
    parser.add_argument(
        "--type",
        choices=SUPPORTED_TYPES,
        help="卡片类型 (quote / contrast / checklist)",
    )
    parser.add_argument(
        "--data",
        type=str,
        help="JSON 字符串数据 (如 '{\"quote\": \"金句测试\"}')",
    )
    parser.add_argument(
        "--data-file",
        type=str,
        help="卡片数据 JSON 文件路径",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="单张卡片输出 PNG 路径",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="批量卡片输出目录",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Chrome 截图超时时间 (默认 30 秒)",
    )

    args = parser.parse_args()

    # 模式 1: 单卡命令行数据输入
    if args.type and args.data:
        if not args.output:
            print("错误: 指定 --type 和 --data 时必须指定 --output /path/to/card.png", file=sys.stderr)
            sys.exit(1)
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"错误: --data 无法解析为有效 JSON: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            out = render_card(args.type, data, args.output, timeout=args.timeout)
            print(f"✓ 渲染成功: {out}")
        except Exception as e:
            print(f"✗ 渲染失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 模式 2: 从 JSON 文件批量渲染
    elif args.data_file:
        out_dir = args.output_dir or (Path(args.output).parent if args.output else "./images")
        try:
            results = render_cards_from_file(args.data_file, out_dir, timeout=args.timeout)
            print(f"✓ 批量渲染完成 ({len(results)} 张):")
            for r in results:
                print(f"  - {r}")
        except Exception as e:
            print(f"✗ 批量渲染失败: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
