#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_knowledge_base.py — 化学知识库分块 + 统计 + dataset_id 映射工具

功能：
1. 扫描 knowledge-base/ 下全部 .md 文档
2. 按 Markdown 二级标题（## ）切块，输出 JSONL（Dify 知识库可用分段格式）
3. 统计每个知识库的行数、字数、二级章节数、代码块数、最大分块长度
4. 生成 dataset_id 占位符 ↔ 知识库文件名映射表
5. 输出三种产物到 output/ 目录：
   - knowledge-base-chunks.jsonl   分块结果（每行一个 JSON 对象）
   - kb-stats.json                 原始统计数据
   - kb-stats.md                   可读的 Markdown 统计报告

用法：
    python scripts/build_knowledge_base.py              # 全量分块 + 统计
    python scripts/build_knowledge_base.py --stats-only # 仅统计不分块
    python scripts/build_knowledge_base.py --chunk-size 500  # 指定最大字符数
    python scripts/build_knowledge_base.py --kb kb-01-课标必考实验库.md  # 指定单个

退出码：
    0 — 成功
    1 — 输入错误（文件不存在、目录无效、JSON 写入失败等）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

# 引入项目内公共模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    DATASET_ID_MAP,
    get_project_root,
    setup_utf8_stdio,
)

setup_utf8_stdio()

__version__ = "1.1.0"


# ───────────────────────────── 数据结构 ─────────────────────────────

@dataclass
class Chunk:
    """单个知识库分块。

    Attributes:
        chunk_id: 唯一标识，格式为 "{source_name}#{index}"。
        source: 来源文件名（如 kb-01-课标必考实验库.md）。
        dataset_placeholder: 对应的 dataset_id 占位符。
        heading: 分块所属二级标题文本。
        line_start: 起始行号（1-based）。
        line_end: 结束行号（1-based，闭区间）。
        char_count: 分块字符数。
        content: 分块纯文本内容。
    """

    chunk_id: str
    source: str
    dataset_placeholder: str
    heading: str
    line_start: int
    line_end: int
    char_count: int
    content: str


@dataclass
class KbStat:
    """单个知识库的统计数据。

    Attributes:
        file_name: 文件名。
        dataset_placeholder: 占位符。
        line_count: 行数。
        char_count: 字符数（含空格、标点）。
        h2_count: 二级标题数。
        h3_count: 三级标题数。
        code_block_count: 代码块数（以 ``` 围栏对计）。
        table_row_count: 表格行数。
        chunk_count: 切块数。
        max_chunk_chars / min_chunk_chars: 最大/最小分块字符数。
        avg_chunk_chars: 平均分块字符数（保留 1 位小数）。
        headings: 去重排序后的二级标题列表。
    """

    file_name: str
    dataset_placeholder: str
    line_count: int
    char_count: int
    h2_count: int
    h3_count: int
    code_block_count: int
    table_row_count: int
    chunk_count: int
    max_chunk_chars: int
    min_chunk_chars: int
    avg_chunk_chars: float
    headings: list[str] = field(default_factory=list)


# ───────────────────────────── 切块逻辑 ─────────────────────────────

H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
H3_PATTERN = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
CODE_FENCE_PATTERN = re.compile(r"^```", re.MULTILINE)
TABLE_ROW_PATTERN = re.compile(r"^\|.*\|\s*$", re.MULTILINE)


def _count_pattern(text: str, pattern: re.Pattern[str]) -> int:
    """统计正则在文本中的匹配次数。

    Args:
        text: 待统计文本。
        pattern: 编译后的正则对象。

    Returns:
        匹配次数。
    """
    return len(pattern.findall(text))


def _make_chunk(source: str, placeholder: str, heading: str,
                line_start: int, line_end: int, content: str,
                index: int) -> Chunk:
    """Chunk 工厂函数（消除重复构造代码）。

    Args:
        source: 来源文件名。
        placeholder: dataset_id 占位符。
        heading: 二级标题。
        line_start / line_end: 起止行号。
        content: 分块内容。
        index: 当前分块在 source 中的序号（1-based）。

    Returns:
        构造好的 Chunk 对象。
    """
    body = content.strip()
    return Chunk(
        chunk_id=f"{source}#{index}",
        source=source,
        dataset_placeholder=placeholder,
        heading=heading,
        line_start=line_start,
        line_end=line_end,
        char_count=len(body),
        content=body,
    )


def split_by_h2(text: str, source_name: str, placeholder: str,
                max_chars: int) -> list[Chunk]:
    """按 Markdown 二级标题切块。

    若某块超过 max_chars，则按段落再次切分。

    Args:
        text: Markdown 全文。
        source_name: 来源文件名。
        placeholder: dataset_id 占位符。
        max_chars: 单块最大字符数。

    Returns:
        Chunk 列表。
    """
    lines = text.split("\n")
    chunks: list[Chunk] = []

    current_heading = "（顶部导言）"
    current_start = 1
    current_buffer: list[str] = []

    def _flush(start: int, end: int) -> None:
        """输出当前缓冲区为一个 Chunk（或多个若超长）。"""
        if not current_buffer:
            return
        body = "\n".join(current_buffer).strip()
        if not body:
            return
        if len(body) <= max_chars:
            chunks.append(_make_chunk(
                source_name, placeholder, current_heading,
                start, end, body, len(chunks) + 1,
            ))
        else:
            _split_long_body(body, start, end)

    def _split_long_body(body: str, start: int, end: int) -> None:
        """将超长 body 按段落二次切分。"""
        para_buffer: list[str] = []
        para_len = 0
        para_start_line = start
        cursor = start
        for line in body.split("\n"):
            cursor += 1
            if para_len + len(line) > max_chars and para_buffer:
                para_text = "\n".join(para_buffer).strip()
                if para_text:
                    chunks.append(_make_chunk(
                        source_name, placeholder, current_heading,
                        para_start_line, cursor - 1,
                        para_text, len(chunks) + 1,
                    ))
                para_buffer = [line]
                para_len = len(line)
                para_start_line = cursor
            else:
                para_buffer.append(line)
                para_len += len(line) + 1
        if para_buffer:
            para_text = "\n".join(para_buffer).strip()
            if para_text:
                chunks.append(_make_chunk(
                    source_name, placeholder, current_heading,
                    para_start_line, end,
                    para_text, len(chunks) + 1,
                ))

    for idx, line in enumerate(lines, start=1):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            _flush(current_start, idx - 1)
            current_heading = m.group(1).strip()
            current_start = idx
            current_buffer = [line]
        else:
            current_buffer.append(line)
    _flush(current_start, len(lines))

    return chunks


# ───────────────────────────── 统计逻辑 ─────────────────────────────

def stat_kb(md_path: Path, placeholder: str, max_chars: int) -> tuple[KbStat, list[Chunk]]:
    """统计单个知识库文件并切分。

    Args:
        md_path: Markdown 文件路径。
        placeholder: dataset_id 占位符。
        max_chars: 单块最大字符数。

    Returns:
        (KbStat, list[Chunk]) 元组。

    Raises:
        OSError: 文件读取失败时抛出（由调用方捕获）。
    """
    text = md_path.read_text(encoding="utf-8")
    chunks = split_by_h2(text, md_path.name, placeholder, max_chars)

    char_sizes = [c.char_count for c in chunks]
    headings = sorted({c.heading for c in chunks})

    stat = KbStat(
        file_name=md_path.name,
        dataset_placeholder=placeholder,
        line_count=text.count("\n") + 1,
        char_count=len(text),
        h2_count=_count_pattern(text, H2_PATTERN),
        h3_count=_count_pattern(text, H3_PATTERN),
        code_block_count=_count_pattern(text, CODE_FENCE_PATTERN) // 2,
        table_row_count=_count_pattern(text, TABLE_ROW_PATTERN),
        chunk_count=len(chunks),
        max_chunk_chars=max(char_sizes) if char_sizes else 0,
        min_chunk_chars=min(char_sizes) if char_sizes else 0,
        avg_chunk_chars=round(sum(char_sizes) / len(char_sizes), 1) if char_sizes else 0.0,
        headings=headings,
    )
    return stat, chunks


# ───────────────────────────── 报告输出 ─────────────────────────────

def render_md_report(stats: list[KbStat], total_chunks: int) -> str:
    """渲染可读的 Markdown 统计报告。

    Args:
        stats: 各库 KbStat 列表。
        total_chunks: 总分块数。

    Returns:
        Markdown 全文字符串。
    """
    lines = []
    lines.append("# 化学知识库分块统计报告\n")
    lines.append(f"总知识库数: **{len(stats)}** | 总分块数: **{total_chunks}**\n")
    lines.append("\n## 一、整体概览\n")
    lines.append("| 文件 | dataset_id 占位符 | 行数 | 字数 | 分块数 | 最大块 | 最小块 | 平均块 |")
    lines.append("|------|------------------|-----:|-----:|------:|------:|------:|------:|")
    for s in stats:
        lines.append(
            f"| {s.file_name} | `{s.dataset_placeholder}` | {s.line_count} | "
            f"{s.char_count} | {s.chunk_count} | {s.max_chunk_chars} | "
            f"{s.min_chunk_chars} | {s.avg_chunk_chars} |"
        )

    lines.append("\n## 二、结构特征\n")
    lines.append("| 文件 | 二级标题数 | 三级标题数 | 代码块数 | 表格行数 |")
    lines.append("|------|---------:|---------:|--------:|--------:|")
    for s in stats:
        lines.append(
            f"| {s.file_name} | {s.h2_count} | {s.h3_count} | "
            f"{s.code_block_count} | {s.table_row_count} |"
        )

    lines.append("\n## 三、章节清单\n")
    for s in stats:
        lines.append(f"### {s.file_name}")
        for h in s.headings:
            lines.append(f"- {h}")
        lines.append("")

    # 扩充建议
    thin = [s for s in stats if s.char_count < 2000 or s.h2_count < 4]
    if thin:
        lines.append("\n## 四、扩充建议\n")
        lines.append("以下知识库内容偏薄，建议导入 Dify 前补充：\n")
        for s in thin:
            lines.append(
                f"- **{s.file_name}**：{s.char_count} 字 / {s.h2_count} 个二级章节，"
                f"建议扩充到 3000 字以上、至少 5 个完整实验条目。"
            )

    return "\n".join(lines) + "\n"


def render_mapping(stats: list[KbStat]) -> str:
    """渲染 dataset_id 占位符 ↔ 知识库文件名映射表。

    Args:
        stats: 各库 KbStat 列表。

    Returns:
        Markdown 表格字符串。
    """
    lines = ["# dataset_id 占位符 ↔ 知识库文件名映射\n"]
    lines.append("| 占位符 | 知识库文件 | 分块数 | 字数 |")
    lines.append("|--------|-----------|------:|-----:|")
    for s in stats:
        lines.append(
            f"| `{s.dataset_placeholder}` | {s.file_name} | "
            f"{s.chunk_count} | {s.char_count} |"
        )
    return "\n".join(lines) + "\n"


# ───────────────────────────── 主流程 ─────────────────────────────

def main() -> int:
    """主入口：扫描知识库、分块、统计、输出产物。

    Returns:
        0 — 成功；1 — 输入错误或 IO 失败。
    """
    parser = argparse.ArgumentParser(description="化学知识库分块 + 统计")
    parser.add_argument("--kb-dir", default="knowledge-base", help="知识库目录（相对项目根）")
    parser.add_argument("--output-dir", default="output", help="产物输出目录（相对项目根）")
    parser.add_argument("--kb", help="仅处理单个文件（文件名，非路径）")
    parser.add_argument("--chunk-size", type=int, default=800,
                        help="单个分块最大字符数（超出再按段落切，默认 800）")
    parser.add_argument("--stats-only", action="store_true",
                        help="仅统计，不输出 JSONL")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览不写入文件（仅打印计划）")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    project_root = get_project_root(__file__)
    kb_dir = (project_root / args.kb_dir).resolve()
    out_dir = (project_root / args.output_dir).resolve()

    if not kb_dir.exists():
        sys.stderr.write(f"[FATAL] 知识库目录不存在: {kb_dir}\n")
        return 1

    if args.dry_run:
        print("[DRY-RUN] 模式开启，不会写入任何文件")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    if args.kb:
        files = [kb_dir / args.kb]
        if not files[0].exists():
            sys.stderr.write(f"[FATAL] 文件不存在: {files[0]}\n")
            return 1
    else:
        files = sorted(kb_dir.glob("kb-*.md"))

    if not files:
        sys.stderr.write(f"[FATAL] {kb_dir} 下未找到 kb-*.md 文件\n")
        return 1

    print("=== 化学知识库分块与统计 ===")
    print(f"知识库目录: {kb_dir}")
    print(f"输出目录:   {out_dir}")
    print(f"分块上限:   {args.chunk_size} 字符")
    print(f"待处理文件: {len(files)} 个")

    all_stats: list[KbStat] = []
    all_chunks: list[Chunk] = []

    for f in files:
        placeholder = DATASET_ID_MAP.get(f.name)
        if not placeholder:
            print(f"[SKIP] {f.name} 不在 DATASET_ID_MAP，跳过")
            continue
        print(f"[处理] {f.name}  →  {placeholder}")
        try:
            stat, chunks = stat_kb(f, placeholder, args.chunk_size)
        except OSError as exc:
            sys.stderr.write(f"[ERROR] 读取 {f.name} 失败: {exc}\n")
            return 1
        all_stats.append(stat)
        all_chunks.extend(chunks)
        print(f"        行数={stat.line_count} 字数={stat.char_count} "
              f"分块数={stat.chunk_count} H2={stat.h2_count}")

    if args.dry_run:
        print(f"\n[DRY-RUN] 预定写出 {len(all_chunks)} 条分块到 {out_dir}/")
        print(f"[DRY-RUN] 预定写出 kb-stats.json / kb-stats.md / dataset-id-mapping.md")
        print(f"\n=== 完成（dry-run，未实际写入）===")
        print(f"知识库总数: {len(all_stats)}")
        print(f"分块总数:   {len(all_chunks)}")
        print(f"总字数:     {sum(s.char_count for s in all_stats)}")
        return 0

    # 写 JSONL
    try:
        if not args.stats_only:
            jsonl_path = out_dir / "knowledge-base-chunks.jsonl"
            with jsonl_path.open("w", encoding="utf-8") as fh:
                for ck in all_chunks:
                    fh.write(json.dumps(asdict(ck), ensure_ascii=False) + "\n")
            print(f"\n[写出] {jsonl_path}  ({len(all_chunks)} 条分块)")

        # 写 kb-stats.json
        stats_json_path = out_dir / "kb-stats.json"
        with stats_json_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "knowledge_bases": [asdict(s) for s in all_stats],
                    "total_chunks": len(all_chunks),
                    "chunk_size_limit": args.chunk_size,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"[写出] {stats_json_path}")

        # 写 kb-stats.md
        stats_md_path = out_dir / "kb-stats.md"
        stats_md_path.write_text(
            render_md_report(all_stats, len(all_chunks)),
            encoding="utf-8",
        )
        print(f"[写出] {stats_md_path}")

        # 写 dataset-id-mapping.md
        mapping_path = out_dir / "dataset-id-mapping.md"
        mapping_path.write_text(render_mapping(all_stats), encoding="utf-8")
        print(f"[写出] {mapping_path}")
    except OSError as exc:
        sys.stderr.write(f"[ERROR] 写入产物失败: {exc}\n")
        return 1

    print(f"\n=== 完成 ===")
    print(f"知识库总数: {len(all_stats)}")
    print(f"分块总数:   {len(all_chunks)}")
    print(f"总字数:     {sum(s.char_count for s in all_stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
