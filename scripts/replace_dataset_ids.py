#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replace_dataset_ids.py — 批量替换 agents/*.yml 中的 dataset_id 占位符

将所有 `REPLACE_WITH_HX_*` 占位符替换为真实的 Dify dataset_id。
配合 `validate_agents.py`（检测占位符）和 `build_knowledge_base.py`（生成映射）使用。

前置条件：
    1. 在 Dify 中创建 6 个知识库，获取每个库的 dataset_id
    2. 整理为 mapping.json 文件（格式见下方示例）
    3. 运行本脚本完成替换

mapping.json 格式示例：
    {
      "REPLACE_WITH_HX_01_KEBIAO_BIKAO": "a1b2c3d4-0001-...",
      "REPLACE_WITH_HX_02_WEIXIAN_FENGXIAN": "a1b2c3d4-0002-...",
      "REPLACE_WITH_HX_03_BIANLIANG_TANJIU": "a1b2c3d4-0003-...",
      "REPLACE_WITH_HX_04_JUJIA_TUOZHAN": "a1b2c3d4-0004-...",
      "REPLACE_WITH_HX_05_ANQUAN_CHUANGGUAN": "a1b2c3d4-0005-...",
      "REPLACE_WITH_HX_06_KAODIAN_SUCHA": "a1b2c3d4-0006-..."
    }

用法：
    python scripts/replace_dataset_ids.py --mapping mapping.json
    python scripts/replace_dataset_ids.py --mapping mapping.json --dry-run
    python scripts/replace_dataset_ids.py --mapping mapping.json --backup
    python scripts/replace_dataset_ids.py --mapping mapping.json --file agents/agent-01-智能助教.yml

退出码：
    0 — 全部替换成功（或 --dry-run 预览完成）
    1 — 至少一个文件替换失败 / mapping 缺失占位符
    2 — 环境错误（mapping 文件不存在、JSON 解析失败等）
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    PLACEHOLDER_PATTERN,
    VALID_PLACEHOLDERS,
    get_project_root,
    setup_utf8_stdio,
)

setup_utf8_stdio()

__version__ = "1.0.0"


# ───────────────────────────── 工具函数 ─────────────────────────────

def load_mapping(mapping_path: Path) -> dict[str, str]:
    """加载并验证 mapping.json。

    Args:
        mapping_path: mapping.json 文件路径。

    Returns:
        {占位符: 真实 dataset_id} 字典。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: JSON 解析失败或占位符命名不合法。
    """
    if not mapping_path.exists():
        raise FileNotFoundError(f"mapping 文件不存在: {mapping_path}")
    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: {exc}")

    if not isinstance(mapping, dict):
        raise ValueError("mapping.json 顶层必须是 JSON 对象")

    # 验证 key 是否全部为合法占位符
    invalid_keys = set(mapping.keys()) - VALID_PLACEHOLDERS
    if invalid_keys:
        raise ValueError(
            f"mapping.json 含未知占位符（命名不规范）: {sorted(invalid_keys)}"
        )

    # 验证 value 是否非空字符串
    empty_vals = [k for k, v in mapping.items() if not isinstance(v, str) or not v.strip()]
    if empty_vals:
        raise ValueError(f"mapping.json 中以下 key 的 value 为空: {empty_vals}")

    return mapping


def find_yml_files(agents_dir: Path, single_file: str | None) -> list[Path]:
    """获取待处理的 YML 文件列表。

    Args:
        agents_dir: agents/ 目录路径。
        single_file: 若指定，仅处理该文件（相对项目根路径）。

    Returns:
        待处理 YML 文件 Path 列表。
    """
    if single_file:
        target = (get_project_root(__file__) / single_file).resolve()
        if not target.exists():
            raise FileNotFoundError(f"指定文件不存在: {target}")
        return [target]
    return sorted(agents_dir.glob("*.yml"))


def replace_in_file(yml_path: Path, mapping: dict[str, str],
                    dry_run: bool = False) -> tuple[int, dict[str, int]]:
    """替换单个 YML 文件中的占位符。

    Args:
        yml_path: 待处理文件路径。
        mapping: {占位符: 真实 ID} 映射。
        dry_run: True 仅预览，不写文件。

    Returns:
        (替换总数, {占位符: 替换次数}) 元组。
    """
    original = yml_path.read_text(encoding="utf-8")
    counter: dict[str, int] = {}

    def _replace(match: re.Match) -> str:  # type: ignore[name-defined]
        placeholder = match.group(0)
        if placeholder in mapping:
            counter[placeholder] = counter.get(placeholder, 0) + 1
            return mapping[placeholder]
        return placeholder

    import re  # 局部 import 避免顶层循环依赖
    new_text = PLACEHOLDER_PATTERN.sub(_replace, original)

    if counter and not dry_run:
        yml_path.write_text(new_text, encoding="utf-8")

    return sum(counter.values()), counter


# ───────────────────────────── 主流程 ─────────────────────────────

def main() -> int:
    """主入口。

    Returns:
        0 — 成功；1 — 部分失败；2 — 环境错误。
    """
    parser = argparse.ArgumentParser(
        description="批量替换 agents/*.yml 中的 dataset_id 占位符"
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="mapping.json 文件路径（含 {占位符: 真实 dataset_id} 映射）",
    )
    parser.add_argument(
        "--dir",
        default="agents",
        help="YML 所在目录（默认 agents，相对项目根）",
    )
    parser.add_argument(
        "--file",
        help="仅替换单个文件（路径相对项目根，如 agents/agent-01-智能助教.yml）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：显示替换计划但不实际写入",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="替换前备份原文件为 .bak（仅在非 dry-run 模式生效）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    project_root = get_project_root(__file__)
    mapping_path = (project_root / args.mapping).resolve()
    agents_dir = (project_root / args.dir).resolve()

    # 1. 加载 mapping
    try:
        mapping = load_mapping(mapping_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"[FATAL] {exc}\n")
        return 2

    print("=== dataset_id 占位符批量替换 ===")
    print(f"mapping 文件: {mapping_path}")
    print(f"已配置占位符: {len(mapping)} / {len(VALID_PLACEHOLDERS)}")
    missing = VALID_PLACEHOLDERS - set(mapping.keys())
    if missing:
        print(f"⚠️  mapping 中缺失: {sorted(missing)}")
        print("   缺失的占位符不会被替换（保持原样）")

    # 2. 收集待处理文件
    try:
        files = find_yml_files(agents_dir, args.file)
    except FileNotFoundError as exc:
        sys.stderr.write(f"[FATAL] {exc}\n")
        return 2

    if not files:
        sys.stderr.write(f"[FATAL] {agents_dir} 下未找到 .yml 文件\n")
        return 2

    print(f"待处理文件: {len(files)} 个")
    if args.dry_run:
        print("[DRY-RUN] 模式开启，不会写入任何文件")
    if args.backup and not args.dry_run:
        print("[BACKUP] 替换前将备份原文件为 .bak")
    print()

    # 3. 逐文件替换
    total_replaced = 0
    files_changed = 0
    files_failed: list[tuple[Path, str]] = []

    for yml_path in files:
        rel = yml_path.relative_to(project_root)
        try:
            # 备份
            if args.backup and not args.dry_run:
                backup_path = yml_path.with_suffix(yml_path.suffix + ".bak")
                shutil.copy2(yml_path, backup_path)

            count, counter = replace_in_file(yml_path, mapping, args.dry_run)
            total_replaced += count
            if count > 0:
                files_changed += 1
                detail = ", ".join(f"{k}×{v}" for k, v in sorted(counter.items()))
                tag = "[预览]" if args.dry_run else "[替换]"
                print(f"{tag} {rel}: {count} 处（{detail}）")
            else:
                print(f"[跳过] {rel}: 无占位符")
        except OSError as exc:
            files_failed.append((yml_path, str(exc)))
            print(f"[失败] {rel}: {exc}")

    # 4. 汇总
    print()
    print("=" * 60)
    print(f"总计替换: {total_replaced} 处")
    print(f"涉及文件: {files_changed} 个（共扫描 {len(files)} 个）")
    if files_failed:
        print(f"失败文件: {len(files_failed)} 个")
        for p, err in files_failed:
            print(f"  - {p.name}: {err}")
        return 1
    if total_replaced == 0:
        print("提示：未替换任何占位符。请检查 YML 中是否仍存在 REPLACE_WITH_HX_* 标记，")
        print("     或运行 python scripts/validate_agents.py 查看占位符分布。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
