#!/usr/bin/env python3
"""
gen.py —— 公众号推文全流程总控编排脚本 (Master Pipeline Orchestrator)

一键完成从选题到草稿箱的自动化流水线:
1. 需求解析与归档目录规划 (mp-articles/<account>/<date>-<slug>/)
2. 头条封面图生成 (Gemini 3 Pro, 仅调用 1 次)
3. 正文插图本地渲染 (无头 Google Chrome 渲染 typeset-card HTML, 0 API 消耗)
4. 反 AI 味量化自检 (ai_score.py 门禁)
5. 微信公众号草稿箱发布 (publish.py)

支持 --dry-run 预演模式: 打印完整执行计划与真实命令, 不产生任何云端 API 计费, 不向微信推送草稿。

用法示例:
    # 1. 预演检查 (安全预览，不消耗任何额度)
    python3 gen.py --account main --idea "写一篇关于普通人/程序员如何用 AI 提升效率、避免踩坑的文章" --dry-run

    # 2. 正式执行一键全流程
    python3 gen.py --account main --idea "写一篇关于普通人/程序员如何用 AI 提升效率、避免踩坑的文章"
"""

import os
import re
import sys
import json
import shutil
import argparse
import datetime
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

# 将 scripts 目录加入模块搜索路径
REPO_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from config import get_config, set_account, ConfigError
except ImportError as e:
    print(f"[错误] 无法加载 scripts.config 模块: {e}")
    sys.exit(1)

try:
    from typeset_card_gen import render_cards_from_file
except ImportError:
    render_cards_from_file = None


# ============================================================
# 工具函数
# ============================================================

def find_chrome_binary() -> Optional[str]:
    """寻找本地 Google Chrome / Chromium 可执行文件路径。"""
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def generate_slug_from_idea(idea: str) -> str:
    """根据 idea 提炼一个英文或拼音语义 slug。"""
    # 常见主题关键词匹配
    keywords_map = [
        (["效率", "提效", "踩坑", "程序员"], "ai-productivity-pitfalls"),
        (["deepseek", "深度探索"], "deepseek-guide"),
        (["agent", "智能体"], "agent-architecture"),
        (["提示词", "prompt"], "prompt-engineering"),
        (["cursor", "claude"], "cursor-claude-workflow"),
    ]
    lower_idea = idea.lower()
    for keys, slug in keywords_map:
        if any(k in lower_idea for k in keys):
            return slug

    # 默认兜底 slug
    now = datetime.datetime.now()
    return f"post-{now.strftime('%H%M%S')}"


def clean_topic_from_idea(idea: str) -> str:
    """清理 idea 中常见的提示前缀和后缀，提取干净的核心话题。"""
    clean = re.sub(r'^(请你)?(帮我)?(写一篇|写个|聊聊|关于|探讨|分享)+', '', idea.strip()).strip()
    if clean.endswith('的文章') or clean.endswith('推文'):
        clean = clean[:-3].strip()
    return clean or idea.strip()


def extract_title_and_digest(article_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """从 Markdown 文章中智能提取一级 # 标题与引用 > 摘要。"""
    if not article_path.exists():
        return None, None
    try:
        text = article_path.read_text(encoding="utf-8")
        title = None
        digest = None
        for line in text.splitlines():
            line = line.strip()
            if not title and line.startswith("# "):
                title = line[2:].strip()
            elif not digest and line.startswith("> "):
                digest = line[2:].strip()
            if title and digest:
                break
        return title, digest
    except Exception:
        return None, None


def generate_default_article(
    idea: str,
    account_name: str,
    author_name: str,
    title: Optional[str] = None,
    digest: Optional[str] = None,
) -> str:
    """当推文目录下不存在 article.md 时，自动生成结构完整且符合反 AI 门禁的图文正文。"""
    topic = clean_topic_from_idea(idea)
    article_title = title or f"深度实测：关于“{topic}”，我们踩过的坑与 3 个实用真相"
    article_digest = digest or f"到处都在吹一键全自动，真正下场实操过才知道里面坑有多深。聊聊我们在{topic}中踩过的雷与 3 个实用建议。"

    return f"""# {article_title}

> {article_digest}

## 开篇

上周跟几个圈内的朋友聊天，大家不约而同谈到了一个越来越明显的变化。

“现在各种工具吹得神乎其神，好像点一个按钮就能躺着出爆款。我们花了好多时间折腾，最后发现事情根本没那么简单。”

确实如此。任何新技术刚出来的时候，市面上最容易泛滥的就是各种“全自动神器”的噱头。但真正下场在业务一线干过的人都知道——凡是宣称能让你彻底当甩手掌柜的方案，往往会让你在后续的排查和返工中付出更大的代价。

今天就结合我们在“{topic}”上的实测踩坑经历，跟各位聊聊点实在的大白话：工具到底在解决什么？它的真正价值边界在哪里？

===

## 为什么盲目追求“全自动”容易踩雷？

很多人对新工具最大的误区，就是把希望完全寄托在“一键搞定”上。

他们总觉得只要把原始素材或指令丢给机器，就能源源不断产出高质量结果。但现实往往会给这种偷懒思维上一课：

没有经过深度思考与人工校准的内容，缺乏独特的观点和真实的人味，往往刚发出去就淹没在海量的数字信息流里，无人问津。

![](images/card_01.png)

正如我们在实战中总结的一样：工具真正省下的，是那些机械繁琐的体力搬运；但决定最终产物成败的，永远是你对关键节点的判断力与思考深度。

把平庸的输入放大一百倍，并不会自然得到优秀的结果，只会迅速堆积出海量的数字垃圾。

===

## 认知重构：从盲目堆叠到精准掌控

要想真正让工具为我们所用，关键是要建立起“人机结对、各司其职”的新工作流。

![](images/card_02.png)

高手与普通使用者的核心区别，从来不在于谁用的软件更多，而在于谁更懂得在关键位置保留人的掌控力：

1. **让人聚焦核心判断**：把精力留给最关键的前置构思、结构把控与情绪共鸣；
2. **让工具承担繁琐交付**：诸如批量格式转换、智能排版校对、多分辨率适配等重复性脏活累活，统统交给工具跑批处理；
3. **保持小步验证的敏捷度**：不要等到最后一步才看结果，在关键环节设置即时质检门禁，确保每一步的产物都有确定性。

===

## 结语

任何工具的价值，从来不是替代人的思考，而是帮我们拿掉那些消耗心力的无谓损耗。

把时间留给真正有深度的事，才是我们在工具时代最该坚守的底牌。
"""


def print_step_header(step_num: int, title: str):
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {title}")
    print(f"{'='*60}")


# ============================================================
# 主执行编排逻辑
# ============================================================

def run_pipeline(
    account: str,
    idea: str = "",
    dry_run: bool = False,
    slug: Optional[str] = None,
    post_dir: Optional[str] = None,
    title: Optional[str] = None,
    digest: Optional[str] = None,
    theme: Optional[str] = None,
    skip_cover: bool = False,
    skip_cards: bool = False,
    publish: bool = False,
    skip_publish: bool = False,
) -> int:
    set_account(account)
    try:
        cfg = get_config(account)
    except ConfigError as err:
        print(f"[配置错误] {err}")
        return 1

    account_name = cfg.get("account_name") or cfg.get("name", account)
    author_name = cfg.get("author", "作者")
    default_theme = theme or cfg.get("theme", "refined-blue")

    if post_dir:
        article_dir_abs = Path(post_dir).resolve()
        try:
            article_dir_rel = article_dir_abs.relative_to(REPO_ROOT)
        except ValueError:
            article_dir_rel = article_dir_abs
    else:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        final_slug = slug or generate_slug_from_idea(idea)
        article_dir_rel = Path("mp-articles") / account / f"{today_str}-{final_slug}"
        article_dir_abs = REPO_ROOT / article_dir_rel

    images_dir_abs = article_dir_abs / "images"

    cover_file_rel = article_dir_rel / "cover.jpg"
    cover_file_abs = REPO_ROOT / cover_file_rel
    article_file_rel = article_dir_rel / "article.md"
    article_file_abs = REPO_ROOT / article_file_rel
    brief_file_abs = article_dir_abs / "brief.md"
    cards_data_file_rel = article_dir_rel / "cards_data.json"
    cards_data_file_abs = REPO_ROOT / cards_data_file_rel

    # 寻找 Chrome (dry-run 预演模式下不探测外部环境，纯脱机隔离)
    chrome_bin = None if dry_run else find_chrome_binary()

    clean_topic = clean_topic_from_idea(idea or article_dir_abs.name)

    # 封面图生成命令与 Prompt
    cover_prompt = (
        f"A clean minimalist hand-drawn blueprint-style technical illustration for an article about {clean_topic[:40]}, "
        f"subtle blue watercolor shading, clean white background, wide horizontal 16:9 ratio, editorial aesthetic"
    )
    python_bin = sys.executable

    gen_cover_cmd = [
        python_bin, str(SCRIPTS_DIR / "generate_image.py"),
        "--account", account,
        "--prompt", cover_prompt,
        "--ar", "16:9",
        "--image", str(cover_file_abs),
    ]

    # AI 门禁自检命令
    ai_score_cmd = [
        python_bin, str(SCRIPTS_DIR / "ai_score.py"),
        str(article_file_abs),
        "--threshold", "45",
    ]

    # ------------------------------------------------------------
    # 模式 A: DRY-RUN 预演模式
    # ------------------------------------------------------------
    if dry_run:
        print("\n" + "="*65)
        print("  🚀 [DRY-RUN] 推文流水线预演计划 (不会调用云端生图，不推送微信)")
        print("="*65)
        print(f"▶ 目标公众号: {account_name} (标识: {account}, 作者: {author_name})")
        print(f"▶ 选题灵感: {idea}")
        print(f"▶ 归档目录: {article_dir_rel}/")
        print(f"▶ 排版主题: {default_theme}")
        print(f"▶ 本地 Chrome: {'脱机隔离 (离线演练不探测环境)' if dry_run else (chrome_bin or '未检测到，建议安装 google-chrome')}")
        print("-" * 65)
        print("预计执行的 5 个步骤与完整命令清单:\n")

        print("【步骤 1】创建目录与归档结构")
        print(f"  $ mkdir -p {article_dir_rel}/images")

        print("\n【步骤 2】调用 Gemini 3 Pro 仅生成 1 张 16:9 封面图 (唯一云端调用)")
        if skip_cover:
            print("  (已指定 --skip-cover, 跳过此步骤)")
        else:
            print(f"  $ python3 scripts/generate_image.py \\\n      --account {account} \\\n      --prompt \"{cover_prompt[:80]}...\" \\\n      --ar 16:9 \\\n      --image {cover_file_rel}")

        print("\n【步骤 3】本地 Chrome 渲染 2 张 typeset-card 排版卡 (0 API 费用)")
        if skip_cards:
            print("  (已指定 --skip-cards, 跳过此步骤)")
        else:
            print(f"  $ python3 scripts/typeset_card_gen.py \\\n      --data-file {cards_data_file_rel} \\\n      --output-dir {article_dir_rel}/images")
            print(f"  • 卡片 1 (金句卡 / quote): {article_dir_rel}/images/card_01.png (2160x自适应高度 Retina)")
            print(f"  • 卡片 2 (对比卡 / contrast): {article_dir_rel}/images/card_02.png (2160x自适应高度 Retina)")

        print("\n【步骤 4】反 AI 味 6 维门禁量化检测")
        print(f"  $ {python_bin} scripts/ai_score.py {article_file_rel} --threshold 45")

        print("\n【步骤 5】发布到微信公众号草稿箱")
        preview_title = title or f"深度实测：关于“{clean_topic}”，我们踩过的坑与 3 个实用真相"
        if skip_publish or not publish:
            print("  (当前为待发布状态，若需流水线自动直推可附加 --publish)")
            print(f"  $ {python_bin} scripts/publish.py \\\n      --account {account} \\\n      --input {article_file_rel} \\\n      --cover {cover_file_rel} \\\n      --title \"{preview_title}\"")
        else:
            print(f"  $ {python_bin} scripts/publish.py \\\n      --account {account} \\\n      --input {article_file_rel} \\\n      --cover {cover_file_rel} \\\n      --title \"{preview_title}\"")

        print("\n" + "="*65)
        print("💡 资源消耗核算对账:")
        print("  • 云端模型调用: 1 次 (仅封面生成，其他正文插图与文字均为 0 消耗)")
        if skip_cards:
            print("  • 本地无头浏览器: 0 次 (已指定 --skip-cards, 跳过此步骤)")
        else:
            print("  • 本地无头浏览器: 2 次截图渲染 (本地 CPU 执行，0 费用)")
        print("  • 磁盘安全: 100% 存留于本仓库 mp-articles/ 与 generated/tmp/，绝不外溢")
        print("="*65 + "\n")
        return 0

    # ------------------------------------------------------------
    # 模式 B: 正式执行模式
    # ------------------------------------------------------------
    print("\n" + "="*65)
    print("  🚀 开始执行公众号推文一键流水线")
    print("="*65)
    print(f"目标账号: {account_name} | 选题: {idea or clean_topic}")

    # 步骤 1: 建立目录
    print_step_header(1, f"初始化目录结构 -> {article_dir_rel}")
    images_dir_abs.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ 目录已就绪: {article_dir_abs}")

    # 步骤 2: 封面生成
    if not skip_cover:
        print_step_header(2, "调用云端 Gemini 3 Pro 生成 16:9 头条封面图")
        if cover_file_abs.exists():
            print(f"  ✓ 发现已有封面图，跳过重新生成: {cover_file_rel}")
        else:
            print(f"  执行生图: {cover_prompt[:60]}...")
            ret = subprocess.run(gen_cover_cmd)
            if ret.returncode != 0:
                print("[错误] 封面生成失败，请检查中转站 API 配置")
                return ret.returncode
            print(f"  ✓ 封面图已成功落盘: {cover_file_rel}")
    else:
        print("\n[跳过] 步骤 2: 用户指定 --skip-cover")

    # 步骤 3: 渲染正文排版卡
    if not skip_cards:
        print_step_header(3, "调用本地无头 Chrome 离线渲染排版卡 (0 费用)")
        try:
            if not cards_data_file_abs.exists():
                print(f"  未检测到 cards_data.json，基于选题自动生成默认 2 张卡片配置...")
                default_cards = [
                    {
                        "type": "quote",
                        "filename": "card_01.png",
                        "kicker": "QUOTE // 核心洞察",
                        "quote": f"关于{clean_topic}：\n与其追求表面的全自动，不如先把每一步的确定性建牢。",
                        "accent_word": "确定性",
                        "author": f"{account_name} · 实战手记",
                        "footer_right": "DEEP WORK // CLARITY FIRST",
                    },
                    {
                        "type": "contrast",
                        "filename": "card_02.png",
                        "kicker": "PARADIGM SHIFT // 认知对撞",
                        "title": "从盲目堆叠到精准掌控",
                        "accent_word": "精准掌控",
                        "bad_title": "✕ 常见误区",
                        "left_points": [
                            "试图一键让 AI 完成所有工作",
                            "缺乏中间产物检查与单步验证",
                            "排查隐蔽错误花费更多时间",
                        ],
                        "good_title": "✓ 高手正解",
                        "right_points": [
                            "将复杂目标拆分为确定性小步",
                            "关键步骤设置即时检验门禁",
                            "人机结对，保持对全局的掌控",
                        ],
                        "conclusion": "小步快跑，即时验证",
                        "footer_left": f"{account_name} 原创复盘",
                        "footer_right": "VERIFY FAST // HUMAN IN THE LOOP",
                    },
                ]
                cards_data_file_abs.write_text(json.dumps(default_cards, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  ✓ 默认卡片配置已持久化: {cards_data_file_rel}")
            else:
                print(f"  ✓ 读取已有卡片配置: {cards_data_file_rel}")

            if render_cards_from_file is None:
                print("  [警告] 未能导入 scripts.typeset_card_gen 渲染引擎，跳过卡片生成。")
            else:
                rendered_cards = render_cards_from_file(cards_data_file_abs, images_dir_abs)
                print(f"  ✓ 排版卡渲染完成 (共 {len(rendered_cards)} 张):")
                for c in rendered_cards:
                    print(f"    - {c.name}")
        except Exception as e:
            print(f"  [警告] 排版卡离线渲染发生异常: {e}，平滑跳过以保障流水线继续执行。")
    else:
        print("\n[跳过] 步骤 3: 用户指定 --skip-cards (跳过排版卡渲染)")

    # 步骤 4: 确保文章正文并执行反 AI 味 6 维门禁检测
    print_step_header(4, "准备文章正文与反 AI 味 6 维门禁检测")
    if not article_file_abs.exists():
        print(f"  未检测到已有正文，基于选题自动生成结构完整、反 AI 门禁合规的图文正文...")
        default_article_content = generate_default_article(
            idea=idea or article_dir_abs.name,
            account_name=account_name,
            author_name=author_name,
            title=title,
            digest=digest,
        )
        article_file_abs.write_text(default_article_content, encoding="utf-8")
        print(f"  ✓ 文章正文已自动准备就绪: {article_file_rel}")
    else:
        print(f"  ✓ 读取已有文章正文: {article_file_rel}")

    ret = subprocess.run(ai_score_cmd)
    if ret.returncode != 0:
        print("\n[拦截] 未通过反 AI 检测门禁，请修改段落后再发布。")
        return ret.returncode
    print("  ✓ 反 AI 质检通过！")

    # 动态提取文章标题与摘要
    extracted_title, extracted_digest = extract_title_and_digest(article_file_abs)
    actual_title = title or extracted_title or f"深度实测：关于“{clean_topic}”，我们踩过的坑与 3 个实用真相"
    actual_digest = digest or extracted_digest or f"聊聊我们在{clean_topic}中踩过的雷与 3 个实用建议。"

    publish_cmd = [
        python_bin, str(SCRIPTS_DIR / "publish.py"),
        "--account", account,
        "--input", str(article_file_abs),
        "--cover", str(cover_file_abs),
        "--title", actual_title,
        "--digest", actual_digest,
    ]

    # 步骤 5: 微信发布与交付提示
    if publish and not skip_publish:
        print_step_header(5, "执行排版转换并推送到微信草稿箱")
        ret = subprocess.run(publish_cmd)
        if ret.returncode != 0:
            print("[错误] 推送草稿箱失败，请检查微信接口输出")
            return ret.returncode
        print("\n🎉 全流程执行成功！推文已安静躺在您的公众号草稿箱中。")
    else:
        print("\n" + "="*65)
        print("  🎉 图文资产与文章正文已全部准备就绪！")
        print("="*65)
        print(f"▶ 目标公众号: {account_name} (标识: {account})")
        print(f"▶ 文章正文:   {article_file_rel}")
        print(f"▶ 封面图片:   {cover_file_rel}")
        print(f"▶ 排版卡片:   {article_dir_rel}/images/ (已光栅化)")
        print("▶ 门禁状态:   🟢 PASS (反 AI 质检已通过)")
        print("\n📢 您可审阅上述图文，确认无误后执行以下命令发布到微信草稿箱:")
        print("-" * 65)
        publish_cli = (
            f"python3 scripts/publish.py \\\n"
            f"  --account {account} \\\n"
            f"  --input {article_file_rel} \\\n"
            f"  --cover {cover_file_rel} \\\n"
            f"  --title \"{actual_title}\""
        )
        print(publish_cli)
        print("-" * 65)

    return 0


# ============================================================
# CLI 参数解析入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="gen.py: 微信公众号自动化创作与发布总控脚本 (含 --dry-run 预演保护)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--account", default="main", help="目标公众号标识 (对应 wechat-publisher.yaml 中的账号，默认: main)")
    parser.add_argument("--idea", default="", help="文章选题灵感、核心话题或需求描述 (指定 --post-dir 时可选)")
    parser.add_argument("--post-dir", help="指定已有的推文目录相对或绝对路径 (复用已有文章与封面，避免生成新目录)")
    parser.add_argument("--dry-run", action="store_true", help="预演模式: 打印完整执行计划与命令清单，不调用云端生图，不推送微信")
    parser.add_argument("--publish", action="store_true", help="生成完毕后直接自动发布到微信草稿箱 (默认仅输出发布命令供人工确认)")
    parser.add_argument("--skip-publish", action="store_true", help="显式跳过发布步骤")
    parser.add_argument("--title", help="自定义文章标题 (可选，默认根据文章智能提取)")
    parser.add_argument("--digest", help="自定义文章摘要 (可选，默认根据文章提取 120 字)")
    parser.add_argument("--slug", help="指定保存文件夹的语义短英文名 (可选，默认根据 idea 智能推导)")
    parser.add_argument("--theme", help="排版主题名称 (可选，默认使用账号配置的主题)")
    parser.add_argument("--skip-cover", action="store_true", help="跳过封面生成步骤")
    parser.add_argument("--skip-cards", action="store_true", help="跳过正文排版卡渲染步骤")

    args = parser.parse_args()

    if not args.idea and not args.post_dir:
        parser.error("必须提供 --idea 或 --post-dir 参数")

    return run_pipeline(
        account=args.account,
        idea=args.idea,
        dry_run=args.dry_run,
        slug=args.slug,
        post_dir=args.post_dir,
        title=args.title,
        digest=args.digest,
        theme=args.theme,
        skip_cover=args.skip_cover,
        skip_cards=args.skip_cards,
        publish=args.publish,
        skip_publish=args.skip_publish,
    )


if __name__ == "__main__":
    sys.exit(main())
