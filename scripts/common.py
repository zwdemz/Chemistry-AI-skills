#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common.py — 化知星 Skills 项目 Python 工具公共模块

提供跨脚本共享的常量、占位符定义、UTF-8 IO 重定向、项目根定位等基础能力。
被 validate_agents.py / build_knowledge_base.py / replace_dataset_ids.py 共同引用。

使用方式：
    from common import (
        DATASET_ID_MAP, VALID_PLACEHOLDERS, PLACEHOLDER_PATTERN,
        EXPECTED_MODEL_NAME, EXPECTED_MODEL_PROVIDER,
        EXPECTED_RERANKER_MODEL, EXPECTED_RERANKER_PROVIDER,
        EXPECTED_DOCX_PLUGIN, VALID_VERSIONS, VALID_MODES, VALID_STRATEGIES,
        setup_utf8_stdio, get_project_root,
    )
"""

from __future__ import annotations

import sys
from pathlib import Path
import re

__version__ = "1.0.0"
__author__ = "化知星团队"
__created__ = "2026-07-15"

# ───────────────────────────── 版本与白名单 ─────────────────────────────

# Dify DSL schema 主流版本
VALID_VERSIONS = {"0.3.0", "0.1.5", "0.1.4"}

# Dify app.mode 支持的模式
VALID_MODES = {"workflow", "agent-chat", "advanced-chat", "completion", "chat"}

# Agent 推理策略
VALID_STRATEGIES = {"react", "function-call"}

# ───────────────────────────── 模型与插件 ─────────────────────────────

# 主 LLM 模型（火山引擎 MaaS）
EXPECTED_MODEL_NAME = "Doubao-Seed-1.6"
EXPECTED_MODEL_PROVIDER = "langgenius/volcengine_maas/volcengine_maas"

# Reranking 模型（xinference 部署）
EXPECTED_RERANKER_MODEL = "bge-reranker-base"
EXPECTED_RERANKER_PROVIDER = "langgenius/xinference/xinference"

# DOCX 转换插件
EXPECTED_DOCX_PLUGIN = "stvlynn/doc"

# ───────────────────────────── 知识库占位符 ─────────────────────────────

# 6 大化学知识库 dataset_id 占位符 ↔ 文件名映射
DATASET_ID_MAP = {
    "kb-01-课标必考实验库.md":     "REPLACE_WITH_HX_01_KEBIAO_BIKAO",
    "kb-02-危险操作风险库.md":     "REPLACE_WITH_HX_02_WEIXIAN_FENGXIAN",
    "kb-03-变量对照探究实验库.md": "REPLACE_WITH_HX_03_BIANLIANG_TANJIU",
    "kb-04-居家安全拓展实验库.md": "REPLACE_WITH_HX_04_JUJIA_TUOZHAN",
    "kb-05-安全闯关题库.md":       "REPLACE_WITH_HX_05_ANQUAN_CHUANGGUAN",
    "kb-06-初中化学考点速查.md":   "REPLACE_WITH_HX_06_KAODIAN_SUCHA",
}

# 合法的占位符名称集合（用于校验命名规范）
VALID_PLACEHOLDERS = set(DATASET_ID_MAP.values())

# 占位符匹配正则（允许大写字母、数字、下划线）
PLACEHOLDER_PATTERN = re.compile(r"REPLACE_WITH_HX_[A-Z0-9_]+")


# ───────────────────────────── 公共函数 ─────────────────────────────

def setup_utf8_stdio() -> None:
    """强制 stdout/stderr 使用 UTF-8 编码。

    解决 Windows GBK 终端无法输出 emoji/中文字符的问题。
    在 Python 3.7+ 的 sys.stdout 上调用 reconfigure 方法；若不支持则静默忽略。

    Examples:
        >>> setup_utf8_stdio()  # 在 main 函数首行调用
    """
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # 某些环境下 stdout 可能是 StringIO 等不支持 reconfigure 的对象
            pass


def get_project_root(current_file: str | Path | None = None) -> Path:
    """获取项目根目录（scripts/ 的上一级）。

    Args:
        current_file: 调用方的 __file__ 路径。若为 None，则假设调用栈深度为 1
                      （即调用者本身位于 scripts/ 下），自动推断。

    Returns:
        项目根目录的 Path 对象。

    Examples:
        # 在 scripts/validate_agents.py 中调用：
        >>> PROJECT_ROOT = get_project_root(__file__)
    """
    if current_file is None:
        # 退路：假设当前工作目录就是项目根
        return Path.cwd()
    return Path(current_file).resolve().parent.parent


def format_placeholder_summary(counter: dict[str, int]) -> str:
    """格式化占位符统计为可读字符串。

    Args:
        counter: {占位符名: 出现次数} 字典。

    Returns:
        形如 "REPLACE_WITH_HX_01_KEBIAO_BIKAO×3, REPLACE_WITH_HX_06_KAODIAN_SUCHA×2" 的字符串。
    """
    return ", ".join(f"{k}×{v}" for k, v in sorted(counter.items()))
