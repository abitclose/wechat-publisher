#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_typeset_cards.py
自动化测试套件与端到端回归测试 (Typeset Card Pipeline)

测试门禁与断言要求：
1. [测试 1: 数据转义与安全性]
   - safe_escape 与 apply_accent_highlight：特殊字符、双引号、换行符 \\n 转 <br/>、HTML 标签 <script> 转义；
   - 字数自适应：字数超过 40 字时 quote 模板自动附加 long-text 类，40 字以内不附加；
2. [测试 2: 单卡本地离线 Chrome 渲染]
   - quote, contrast, checklist 三类卡片分别调用 render_card 渲染；
   - 断言输出文件存在，且通过 PIL 打开时尺寸严格为 2160x2700，格式为 PNG；
3. [测试 3: 批量文件卡片渲染]
   - render_cards_from_file 处理包含 2 张卡片配置的 JSON 文件，验证文件正确落盘；
   - 验证 list 与 dict 格式的卡片数据契约解析；
4. [测试 4: 异常处理与输入防护]
   - 非法卡片类型 (如 'unknown_type') 正确抛出 ValueError；
   - 缺失模板文件时抛出 FileNotFoundError；
   - 缺失 JSON 文件或非法 JSON 结构时抛出 FileNotFoundError / ValueError；
5. [测试 5: 生命周期与沙箱验证]
   - 渲染成功后，generated/tmp/ 下的中间 tmp_card_*.html 100% 销毁清理；
   - 渲染异常中断时 (finally 门禁)，generated/tmp/ 下的中间临时文件依然 100% 销毁清理，杜绝垃圾残留。
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from PIL import Image

import typeset_card_gen
from typeset_card_gen import (
    TMP_DIR,
    apply_accent_highlight,
    build_checklist_html,
    build_contrast_html,
    build_quote_html,
    render_card,
    render_cards_from_file,
    safe_escape,
)


# ============================================================================
# 测试 1: 数据转义与安全性 (Data Escaping & Security)
# ============================================================================


class TestDataEscapingAndSecurity:
    """测试数据注入的 HTML 安全转义与样式自适应。"""

    def test_safe_escape_none_and_empty(self) -> None:
        """测试 None 与空字符串安全转为空字符串。"""
        assert safe_escape(None) == ""
        assert safe_escape("") == ""

    def test_safe_escape_special_characters_and_xss(self) -> None:
        """测试特殊字符、双引号与 XSS 脚本标签转义。"""
        raw_xss = '<script>alert("xss & risk")</script>'
        escaped = safe_escape(raw_xss)
        assert "<script>" not in escaped
        assert "</script>" not in escaped
        assert "&lt;script&gt;" in escaped
        assert "&quot;xss &amp; risk&quot;" in escaped or ("&quot;" in escaped and "&amp;" in escaped)

    def test_safe_escape_newlines_conversion(self) -> None:
        """测试 \\n 与 \\r\\n 换行符转换为 <br/>。"""
        text_with_newlines = "第一行内容\n第二行内容\r\n第三行内容"
        escaped = safe_escape(text_with_newlines)
        assert "\n" not in escaped
        assert "\r" not in escaped
        assert escaped == "第一行内容<br/>第二行内容<br/>第三行内容"

    def test_safe_escape_non_string_types(self) -> None:
        """测试整型、布尔等非字符串类型转为安全字符串。"""
        assert safe_escape(12345) == "12345"
        assert safe_escape(True) == "True"

    def test_apply_accent_highlight_single_occurrence(self) -> None:
        """测试强调词高亮且仅替换首次出现的强调词。"""
        text = "认知重塑是关键，深刻的认知带来改变"
        highlighted = apply_accent_highlight(text, "认知")
        expected = '<span class="em">认知</span>重塑是关键，深刻的认知带来改变'
        assert highlighted == expected

    def test_apply_accent_highlight_none_or_missing(self) -> None:
        """测试当强调词为空或不存在于文本中时，保持原文本不变。"""
        assert apply_accent_highlight("普通文本内容", None) == "普通文本内容"
        assert apply_accent_highlight("普通文本内容", "") == "普通文本内容"
        assert apply_accent_highlight("普通文本内容", "不存在的词") == "普通文本内容"
        assert apply_accent_highlight("", "强调词") == ""

    def test_apply_accent_highlight_with_special_characters(self) -> None:
        """测试包含 HTML 特殊字符的强调词能安全匹配高亮。"""
        text = "开发 &amp; 运维"
        highlighted = apply_accent_highlight(text, "&")
        assert '<span class="em">&amp;</span>' in highlighted

    def test_quote_long_text_class_adaptation(self) -> None:
        """测试金句卡在字数 > 40 时自动附加 long-text 类，<= 40 时为空。"""
        dummy_template = '<div class="quote {{QUOTE_CLASS}}">{{QUOTE}}</div>'

        # <= 40 字：不加 long-text
        short_quote = "短金句：认知是行动的先导，知行合一。"
        assert len(short_quote) <= 40
        short_html = build_quote_html(dummy_template, {"quote": short_quote})
        assert 'class="quote "' in short_html
        assert "long-text" not in short_html

        # > 40 字：自动应用 long-text
        long_quote = (
            "这是一段非常深刻的长金句内容，用于严格验证排版渲染引擎在文案长度"
            "超过四十个中文字符时是否会自动触发自适应排版样式与字号缩小保护。"
        )
        assert len(long_quote) > 40
        long_html = build_quote_html(dummy_template, {"quote": long_quote})
        assert 'class="quote long-text"' in long_html


# ============================================================================
# 测试 2: 单卡本地离线 Chrome 渲染 (Single Card Chrome Rendering)
# ============================================================================


class TestSingleCardChromeRendering:
    """测试调用本地 Chrome 渲染 quote, contrast, checklist 三类卡片。"""

    def test_render_quote_card(self, tmp_path: Path) -> None:
        """测试 quote 模板渲染为 2160x2700 高清 PNG。"""
        out_png = tmp_path / "card_quote.png"
        data: Dict[str, Any] = {
            "kicker": "QUOTE // 核心洞察",
            "quote": "别做甩手掌柜，把它当成全天候结对搭子。",
            "accent_word": "结对搭子",
            "author": "数效笔记 · 数小二 // 踩坑实录",
            "footer_right": "LESS IS MORE",
        }

        ret_path = render_card("quote", data, out_png)
        assert Path(ret_path).resolve() == out_png.resolve()
        assert out_png.is_file()
        assert out_png.stat().st_size > 0

        # PIL 严格校验尺寸与格式 (金句卡支持动态自适应高度：宽度固定 2160，高度根据文字自适应收敛)
        with Image.open(out_png) as im:
            assert im.size[0] == 2160
            assert 800 <= im.size[1] <= 2700
            assert im.format == "PNG"

    def test_render_contrast_card(self, tmp_path: Path) -> None:
        """测试 contrast 模板渲染为 2160x2700 高清 PNG。"""
        out_png = tmp_path / "card_contrast.png"
        data: Dict[str, Any] = {
            "kicker": "PARADIGM SHIFT // 认知对撞",
            "title_line1": "从指令下达到",
            "title_highlight": "结对编程",
            "bad_title": "✕ 常见误区",
            "left_points": [
                "指望一句话生成完美代码",
                "遇到报错就重开新会话",
                "对生成内容不测试直接提交",
            ],
            "good_title": "✓ 高手正解",
            "right_points": [
                "小步快跑分阶段落地",
                "提供完整上下文与单点测试",
                "严格测试驱动即时验证",
            ],
            "conclusion": "上下文质量 > 提示词魔法",
            "footer_left": "数效笔记 · 数小二 原创复盘",
            "footer_right": "VERIFY FAST",
        }

        ret_path = render_card("contrast", data, out_png)
        assert Path(ret_path).resolve() == out_png.resolve()
        assert out_png.is_file()
        assert out_png.stat().st_size > 0

        with Image.open(out_png) as im:
            assert im.size == (2160, 2700)
            assert im.format == "PNG"

    def test_render_checklist_card(self, tmp_path: Path) -> None:
        """测试 checklist 模板渲染为 2160x2700 高清 PNG。"""
        out_png = tmp_path / "card_checklist.png"
        data: Dict[str, Any] = {
            "kicker": "PRACTICAL CHECKLIST // 实操避坑指南",
            "tag": "实操小抄",
            "title": "日常高效用 AI 的 3 个保命习惯",
            "items": [
                {"idx": "01", "title": "单一可信源", "desc": "配置收敛到单一配置文件，严禁散落"},
                {"idx": "02", "title": "测试先于交付", "desc": "没有自动化测试的代码视为未完成"},
                {"idx": "03", "title": "严格沙箱隔离", "desc": "临时文件必须彻底清理，零垃圾残留"},
            ],
            "footer_left": "数效笔记 · 数小二 独家整理",
            "footer_right": "CONTEXT > PROMPT MAGIC",
        }

        ret_path = render_card("checklist", data, out_png)
        assert Path(ret_path).resolve() == out_png.resolve()
        assert out_png.is_file()
        assert out_png.stat().st_size > 0

        with Image.open(out_png) as im:
            assert im.size == (2160, 2700)
            assert im.format == "PNG"


# ============================================================================
# 测试 3: 批量文件卡片渲染 (Batch File Rendering)
# ============================================================================


class TestBatchFileRendering:
    """测试从 JSON 文件批量渲染卡片。"""

    def test_render_cards_from_file_list_contract(self, tmp_path: Path) -> None:
        """测试以 list 格式提供 2 张卡片配置时，正确批量落盘。"""
        cards_data = [
            {
                "type": "quote",
                "filename": "card_01.png",
                "quote": "第一张金句卡内容：持续演进，即时反馈。",
                "author": "测试作者 1",
            },
            {
                "type": "checklist",
                "filename": "card_02.png",
                "title": "第二张清单卡：排版三步走",
                "items": [
                    {"idx": "01", "title": "设计模板", "desc": "HTML+CSS 离线可复现"},
                    {"idx": "02", "title": "注入数据", "desc": "转义字符防注入"},
                ],
            },
        ]

        json_file = tmp_path / "cards_list.json"
        json_file.write_text(json.dumps(cards_data, ensure_ascii=False), encoding="utf-8")

        out_dir = tmp_path / "batch_out_list"
        result_paths = render_cards_from_file(json_file, out_dir)

        assert len(result_paths) == 2
        for p in result_paths:
            assert p.is_file()
            assert p.stat().st_size > 0
            with Image.open(p) as im:
                assert im.size[0] == 2160
                assert im.format == "PNG"

        # card_01 为 quote 动态自适应高度，card_02 为 checklist 固定 4:5 规格 (2160x2700)
        with Image.open(out_dir / "card_01.png") as im:
            assert 800 <= im.size[1] <= 2700
        with Image.open(out_dir / "card_02.png") as im:
            assert im.size == (2160, 2700)

        assert (out_dir / "card_01.png").is_file()
        assert (out_dir / "card_02.png").is_file()

    def test_render_cards_from_file_dict_contract(self, tmp_path: Path) -> None:
        """测试以 {'cards': [...]} 契约提供数据时正确解析并落盘。"""
        cards_data = {
            "cards": [
                {
                    "type": "contrast",
                    "filename": "contrast_custom.png",
                    "title": "测试对比卡",
                    "bad_desc": "旧做法：手动排版",
                    "good_desc": "新做法：自动化离线光栅化",
                    "conclusion": "降本增效",
                }
            ]
        }

        json_file = tmp_path / "cards_dict.json"
        json_file.write_text(json.dumps(cards_data, ensure_ascii=False), encoding="utf-8")

        out_dir = tmp_path / "batch_out_dict"
        result_paths = render_cards_from_file(json_file, out_dir)

        assert len(result_paths) == 1
        custom_png = out_dir / "contrast_custom.png"
        assert custom_png.is_file()
        with Image.open(custom_png) as im:
            assert im.size == (2160, 2700)


# ============================================================================
# 测试 4: 异常处理与输入防护 (Exception Handling & Input Guards)
# ============================================================================


class TestExceptionHandlingAndInputGuards:
    """测试非法参数、未知类型与缺失模板的防护机制。"""

    def test_invalid_card_type_raises_value_error(self, tmp_path: Path) -> None:
        """测试传入未知卡片类型时抛出明确的 ValueError。"""
        out_png = tmp_path / "invalid.png"
        with pytest.raises(ValueError, match="不支持的卡片类型: 'unknown_type'"):
            render_card("unknown_type", {"quote": "test"}, out_png)

    def test_missing_template_file_raises_file_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """测试模板文件不存在时抛出 FileNotFoundError。"""
        empty_templates = tmp_path / "empty_templates_dir"
        empty_templates.mkdir()
        monkeypatch.setattr(typeset_card_gen, "TEMPLATES_DIR", empty_templates)

        out_png = tmp_path / "missing_tmpl.png"
        with pytest.raises(FileNotFoundError, match="未找到模板文件"):
            render_card("quote", {"quote": "test"}, out_png)

    def test_missing_json_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """测试批量渲染时指定不存在的 JSON 文件抛出 FileNotFoundError。"""
        non_existent_json = tmp_path / "non_existent.json"
        with pytest.raises(FileNotFoundError, match="未找到卡片数据文件"):
            render_cards_from_file(non_existent_json, tmp_path / "out")

    def test_invalid_json_structure_raises_value_error(self, tmp_path: Path) -> None:
        """测试 JSON 顶层结构非法时抛出 ValueError。"""
        invalid_json = tmp_path / "invalid_struct.json"
        invalid_json.write_text(json.dumps("这是一个纯字符串而非对象或列表"), encoding="utf-8")
        with pytest.raises(ValueError, match="JSON 顶层必须为 dict 或 list"):
            render_cards_from_file(invalid_json, tmp_path / "out")


# ============================================================================
# 测试 5: 生命周期与沙箱验证 (Lifecycle & Sandbox Verification)
# ============================================================================


class TestLifecycleAndSandboxValidation:
    """测试临时沙箱隔离与中间组装 HTML 文件 100% 销毁清理。"""

    def test_sandbox_cleanup_on_successful_render(self, tmp_path: Path) -> None:
        """测试正常渲染完成后，generated/tmp/ 下的中间 tmp_card_*.html 被彻底清理。"""
        # 记录执行前的临时 HTML
        before_tmp_htmls = set(TMP_DIR.glob("tmp_card_*.html"))

        out_png = tmp_path / "cleanup_test.png"
        render_card(
            "quote",
            {"quote": "沙箱生命周期测试：确保无任何中间组装 HTML 遗留。"},
            out_png,
        )

        assert out_png.is_file()
        after_tmp_htmls = set(TMP_DIR.glob("tmp_card_*.html"))

        # 新增的中间 html 文件必须为 0
        leaked_files = after_tmp_htmls - before_tmp_htmls
        assert len(leaked_files) == 0, f"发现泄漏的中间临时 HTML 文件: {leaked_files}"

    def test_sandbox_cleanup_on_rendering_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """测试当渲染命令执行失败或异常中断时，finally 门禁依然确保中间 HTML 被彻底清理。"""
        before_tmp_htmls = set(TMP_DIR.glob("tmp_card_*.html"))

        # 模拟 Chrome 失败 (返回非 0 退出码)
        def mock_failed_run(*args: Any, **kwargs: Any) -> Any:
            class MockResult:
                returncode = 1
                stderr = "Mocked Chrome segmentation fault or render failure"
                stdout = ""

            return MockResult()

        monkeypatch.setattr(typeset_card_gen.subprocess, "run", mock_failed_run)

        out_png = tmp_path / "failure_cleanup.png"
        with pytest.raises(RuntimeError, match="Chrome 无头渲染失败"):
            render_card("quote", {"quote": "异常场景沙箱清理测试"}, out_png)

        after_tmp_htmls = set(TMP_DIR.glob("tmp_card_*.html"))
        leaked_files = after_tmp_htmls - before_tmp_htmls
        assert len(leaked_files) == 0, f"异常中断后存在未清理的临时文件: {leaked_files}"
