#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_agents.py — Dify Skills 智能体 YML 批量校验工具

功能：
1. YAML 语法解析
2. 顶层必备字段检查（app / kind / version）
3. app 子字段检查（name / mode / description）
4. workflow 模式结构完整性（含 start + end + 至少 1 个 LLM 节点）
5. agent-chat 模式结构完整性（含 model_config）
6. 依赖插件完整性（volcengine_maas + xinference + stvlynn/doc 如使用 DOCX）
7. 模型一致性（Doubao-Seed-1.6 / langgenius/volcengine_maas/volcengine_maas）
8. dataset_id 占位符检测（REPLACE_WITH_HX_* 未替换告警）
9. 节点-连线连通性检查（非 start 必有入度，非 end 必有出度）
10. 占位符命名一致性（不允许出现未知占位符）

用法：
    python scripts/validate_agents.py
    python scripts/validate_agents.py --dir agents
    python scripts/validate_agents.py --file agents/agent-00-化知星总调度.yml
    python scripts/validate_agents.py --strict   # 把告警也算失败

退出码：
    0 — 全部通过
    1 — 至少一个文件存在错误（或 --strict 模式下存在告警）
    2 — 环境错误（如缺少 PyYAML）
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

# 引入项目内公共模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    DATASET_ID_MAP,
    EXPECTED_DOCX_PLUGIN,
    EXPECTED_MODEL_NAME,
    EXPECTED_MODEL_PROVIDER,
    EXPECTED_RERANKER_MODEL,
    EXPECTED_RERANKER_PROVIDER,
    PLACEHOLDER_PATTERN,
    VALID_MODES,
    VALID_PLACEHOLDERS,
    VALID_STRATEGIES,
    VALID_VERSIONS,
    format_placeholder_summary,
    get_project_root,
    setup_utf8_stdio,
)

setup_utf8_stdio()

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "[FATAL] 缺少 PyYAML，请执行: pip install -r scripts/requirements.txt\n"
    )
    sys.exit(2)


__version__ = "1.1.0"


# ───────────────────────────── 工具函数 ─────────────────────────────

class CheckReport:
    """单文件校验结果容器。

    Attributes:
        file_path: 被校验文件路径。
        errors: 错误消息列表（导致 fail）。
        warnings: 告警消息列表（不导致 fail，但 --strict 模式下计入）。
        info: 信息性消息（仅显示，不影响结果）。
    """

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    @property
    def ok(self) -> bool:
        """是否通过校验（无 error）。"""
        return not self.errors

    def fail(self, msg: str) -> None:
        """记录一条错误消息。"""
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        """记录一条告警消息。"""
        self.warnings.append(msg)

    def log(self, msg: str) -> None:
        """记录一条信息性消息。"""
        self.info.append(msg)


def _walk_nodes(graph: dict[str, Any]) -> dict[str, dict]:
    """返回 node_id → node 字典。

    Args:
        graph: workflow.graph 字典。

    Returns:
        {node_id: node_data} 映射。
    """
    nodes = graph.get("nodes", []) or []
    return {str(n.get("id")): n for n in nodes}


def _walk_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """返回边列表。

    Args:
        graph: workflow.graph 字典。

    Returns:
        edges 列表（每项为 {source, target, ...} 字典）。
    """
    return graph.get("edges", []) or []


def _collect_model_providers(node: dict[str, Any]) -> list[tuple[str, str]]:
    """从节点中抽取 (model_name, provider) 列表。

    Args:
        node: 单个 graph node 字典。

    Returns:
        [(name, provider), ...] 元组列表；无 model 时为空列表。
    """
    data = node.get("data", {}) or {}
    model = data.get("model")
    if not model:
        return []
    name = model.get("name") or ""
    provider = model.get("provider") or ""
    return [(name, provider)]


# ───────────────────────────── 各项检查 ─────────────────────────────

def check_top_level(doc: dict[str, Any], report: CheckReport) -> None:
    """检查顶层字段（app / kind / version）。

    Args:
        doc: YAML 解析后的顶层字典。
        report: 校验结果容器。
    """
    if "app" not in doc or not isinstance(doc["app"], dict):
        report.fail("缺少顶层字段 `app` 或类型不是 dict")
        return
    if doc.get("kind") != "app":
        report.fail(f"kind 字段必须为 'app'，实际为 {doc.get('kind')!r}")
    if str(doc.get("version")) not in VALID_VERSIONS:
        report.warn(f"version={doc.get('version')!r} 非主流版本（推荐 0.3.0）")


def check_app_meta(app: dict[str, Any], report: CheckReport) -> None:
    """检查 app 元信息（name / mode / description）。

    Args:
        app: doc["app"] 字典。
        report: 校验结果容器。
    """
    for key in ("name", "mode", "description"):
        val = app.get(key)
        if not val:
            report.fail(f"app.{key} 为空")
    mode = app.get("mode")
    if mode not in VALID_MODES:
        report.fail(f"app.mode={mode!r} 不是 Dify 支持的模式")
    if len(app.get("description", "")) < 10:
        report.warn("app.description 过短，建议补充说明")


def check_workflow_structure(workflow: dict[str, Any], report: CheckReport) -> None:
    """workflow 结构完整性。"""
    graph = workflow.get("graph")
    if not graph or not isinstance(graph, dict):
        report.fail("workflow.graph 缺失或类型错误")
        return

    nodes = _walk_nodes(graph)
    if not nodes:
        report.fail("graph.nodes 为空")
        return

    type_buckets: dict[str, list[str]] = {}
    for nid, node in nodes.items():
        nd = node.get("data", {}) or {}
        t = nd.get("type") or ""
        type_buckets.setdefault(t, []).append(nid)

    if "start" not in type_buckets or len(type_buckets["start"]) < 1:
        report.fail("缺少 start 节点")
    if "end" not in type_buckets or len(type_buckets["end"]) < 1:
        report.fail("缺少 end 节点")
    if "llm" not in type_buckets:
        report.warn("未发现 LLM 节点（workflow 通常至少需要 1 个）")

    report.log(
        f"节点类型分布: {', '.join(f'{k}={len(v)}' for k, v in sorted(type_buckets.items()))}"
    )

    # 连通性
    edges = _walk_edges(graph)
    in_deg: dict[str, int] = {nid: 0 for nid in nodes}
    out_deg: dict[str, int] = {nid: 0 for nid in nodes}
    for e in edges:
        s = str(e.get("source"))
        t = str(e.get("target"))
        if s in out_deg:
            out_deg[s] += 1
        if t in in_deg:
            in_deg[t] += 1

    for nid, node in nodes.items():
        t = (node.get("data", {}) or {}).get("type")
        if t == "start":
            if out_deg[nid] == 0:
                report.fail(f"start 节点 {nid} 没有出边")
        elif t == "end":
            if in_deg[nid] == 0:
                report.fail(f"end 节点 {nid} 没有入边")
        else:
            if in_deg[nid] == 0:
                report.fail(f"节点 {nid} (type={t}) 没有入边")
            if out_deg[nid] == 0:
                report.fail(f"节点 {nid} (type={t}) 没有出边")

    # 模型一致性
    for nid, node in nodes.items():
        for name, prov in _collect_model_providers(node):
            if name and name != EXPECTED_MODEL_NAME:
                report.fail(
                    f"节点 {nid} model.name={name!r}，与统一模型 {EXPECTED_MODEL_NAME!r} 不一致"
                )
            if prov and prov != EXPECTED_MODEL_PROVIDER:
                report.fail(
                    f"节点 {nid} model.provider={prov!r}，与统一 provider 不一致"
                )


def check_agent_chat_structure(mc: dict[str, Any], report: CheckReport) -> None:
    """agent-chat 结构。"""
    if not isinstance(mc, dict):
        report.fail("model_config 缺失或类型错误")
        return
    model = mc.get("model") or {}
    name = model.get("name")
    prov = model.get("provider")
    if name and name != EXPECTED_MODEL_NAME:
        report.fail(f"model_config.model.name={name!r} 与统一模型不一致")
    if prov and prov != EXPECTED_MODEL_PROVIDER:
        report.fail(f"model_config.model.provider={prov!r} 与统一 provider 不一致")

    agent_mode = mc.get("agent_mode") or {}
    if not agent_mode.get("enabled"):
        report.warn("agent_mode.enabled=false，Agent 可能不会触发工具调用")
    strategy = agent_mode.get("strategy")
    if strategy and strategy not in VALID_STRATEGIES:
        report.warn(f"agent_mode.strategy={strategy!r} 非主流（react/function-call）")

    # 知识库绑定
    dc = mc.get("dataset_configs") or {}
    datasets = ((dc.get("datasets") or {}).get("datasets")) or []
    if not datasets:
        report.warn("dataset_configs.datasets 为空，RAG 未启用")
    else:
        report.log(f"知识库绑定数: {len(datasets)}")
        # reranking
        if not dc.get("reranking_enable"):
            report.warn("reranking_enable=false，建议启用 reranking 提升检索质量")
        else:
            rm = dc.get("reranking_model") or {}
            if rm.get("model") != EXPECTED_RERANKER_MODEL:
                report.warn(
                    f"reranking_model.model={rm.get('model')!r} 与统一 {EXPECTED_RERANKER_MODEL!r} 不一致"
                )
            if rm.get("provider") != EXPECTED_RERANKER_PROVIDER:
                report.warn(
                    f"reranking_model.provider={rm.get('provider')!r} 与统一 provider 不一致"
                )


def check_dependencies(doc: dict[str, Any], uses_docx: bool, report: CheckReport) -> None:
    """检查依赖插件完整性。

    Args:
        doc: YAML 文档字典。
        uses_docx: 是否检测到 DOCX 节点。
        report: 校验结果容器。
    """
    deps = doc.get("dependencies") or []
    has_maas = False
    has_xinference = False
    has_docx = False
    for dep in deps:
        val = dep.get("value") or {}
        ident = val.get("marketplace_plugin_unique_identifier") or val.get(
            "plugin_unique_identifier"
        ) or ""
        if "volcengine_maas" in ident:
            has_maas = True
        if "xinference" in ident:
            has_xinference = True
        if EXPECTED_DOCX_PLUGIN in ident:
            has_docx = True

    if not has_maas:
        report.fail(f"缺少依赖 langgenius/volcengine_maas")
    if not has_xinference:
        report.warn("缺少依赖 langgenius/xinference（reranking 将不可用）")
    if uses_docx and not has_docx:
        report.fail(
            f"使用了 Markdown→DOCX 节点，但缺少依赖 {EXPECTED_DOCX_PLUGIN}"
        )


def scan_placeholders(doc: dict[str, Any], report: CheckReport) -> None:
    """递归扫描整个 doc 中的 REPLACE_WITH_HX_* 占位符。

    Args:
        doc: YAML 文档字典。
        report: 校验结果容器。
    """
    found: list[str] = []

    def _scan(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                _scan(v)
        elif isinstance(obj, list):
            for v in obj:
                _scan(v)
        elif isinstance(obj, str):
            for m in PLACEHOLDER_PATTERN.findall(obj):
                found.append(m)

    _scan(doc)

    if not found:
        report.log("未发现 dataset_id 占位符（可能已替换为真实 ID）")
        return

    unknown = sorted(set(found) - VALID_PLACEHOLDERS)
    if unknown:
        report.fail(f"发现未知占位符（命名不规范）: {', '.join(unknown)}")

    counter: dict[str, int] = {}
    for p in found:
        counter[p] = counter.get(p, 0) + 1
    summary = format_placeholder_summary(counter)
    report.warn(f"检测到未替换的 dataset_id 占位符（共 {len(found)} 处）: {summary}")


def detect_docx_usage(doc: dict[str, Any]) -> bool:
    """检测是否使用了 stvlynn/doc 节点。

    Args:
        doc: YAML 文档字典。

    Returns:
        True 若检测到 DOCX 工具节点；否则 False。
    """
    graph = (doc.get("workflow") or {}).get("graph") or {}
    for node in graph.get("nodes", []) or []:
        data = node.get("data") or {}
        if data.get("type") == "tool":
            provider = str(data.get("provider_id") or "") + " " + str(
                data.get("provider_name") or ""
            )
            tool_name = str(data.get("tool_name") or "")
            if EXPECTED_DOCX_PLUGIN in provider or "docx" in tool_name.lower():
                return True
    return False


# ───────────────────────────── 主流程 ─────────────────────────────

def validate_file(yml_path: Path) -> CheckReport:
    """校验单个 YML 文件的完整流程。

    Args:
        yml_path: 待校验文件路径。

    Returns:
        CheckReport 对象，包含所有错误、告警和信息消息。
    """
    report = CheckReport(yml_path)

    # 1. 读取
    try:
        text = yml_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.fail(f"读取失败: {exc}")
        return report

    # 2. YAML 解析
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        report.fail(f"YAML 语法错误: {exc}")
        return report

    if not isinstance(doc, dict):
        report.fail("YAML 顶层不是 dict")
        return report

    # 3. 顶层
    check_top_level(doc, report)
    app = doc.get("app") or {}
    if not isinstance(app, dict):
        # check_top_level 已 fail，后续无法继续
        return report

    # 4. 元信息
    check_app_meta(app, report)

    # 5. 结构
    mode = app.get("mode")
    uses_docx = detect_docx_usage(doc)
    if uses_docx:
        report.log("检测到 Markdown→DOCX 节点")
    if mode == "workflow":
        wf = doc.get("workflow")
        if not isinstance(wf, dict):
            report.fail("缺少 workflow 字段")
        else:
            check_workflow_structure(wf, report)
    elif mode in {"agent-chat", "advanced-chat", "chat"}:
        mc = doc.get("model_config")
        check_agent_chat_structure(mc or {}, report)

    # 6. 依赖
    check_dependencies(doc, uses_docx, report)

    # 7. 占位符
    scan_placeholders(doc, report)

    return report


def main() -> int:
    """主入口：解析参数，批量校验 YML，输出汇总结果。

    Returns:
        0 — 全部通过；1 — 至少一个失败；2 — 环境错误。
    """
    parser = argparse.ArgumentParser(
        description="Dify Skills 智能体 YML 批量校验"
    )
    parser.add_argument(
        "--dir",
        default="agents",
        help="智能体目录（默认 agents，相对于项目根）",
    )
    parser.add_argument(
        "--file",
        help="仅校验单个文件（路径相对于项目根，如 agents/agent-00-化知星总调度.yml）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：告警也算失败",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    # 解析路径（相对于项目根，即 scripts 的上一级）
    project_root = get_project_root(__file__)

    if args.file:
        target_file = project_root / args.file
        if not target_file.exists():
            sys.stderr.write(f"[FATAL] 文件不存在: {target_file}\n")
            return 2
        files = [target_file]
    else:
        target_dir = (project_root / args.dir).resolve()
        if not target_dir.exists():
            sys.stderr.write(f"[FATAL] 目录不存在: {target_dir}\n")
            return 2
        files = sorted(target_dir.glob("*.yml"))

    if not files:
        sys.stderr.write(f"[FATAL] 未找到任何 .yml 文件于 {args.dir}\n")
        return 2

    total = len(files)
    passed = 0
    failed: list[CheckReport] = []
    warned: list[CheckReport] = []

    print(f"=== Dify Skills 智能体校验 ===")
    print(f"项目根: {project_root}")
    print(f"待校验文件: {total} 个")

    for idx, f in enumerate(files, 1):
        rel = f.relative_to(project_root)
        print(f"[{idx}/{total}] {rel}")
        report = validate_file(f)

        for line in report.info:
            print(f"    ℹ️  {line}")

        if report.errors:
            failed.append(report)
            for err in report.errors:
                print(f"    ❌ {err}")
        else:
            passed += 1

        for w in report.warnings:
            print(f"    ⚠️  {w}")
            if args.strict and report not in failed:
                warned.append(report)

        print()

    print("=" * 60)
    print(f"总计: {total} | 通过: {passed} | 失败: {len(failed)}")
    if failed:
        print("失败文件:")
        for r in failed:
            print(f"  - {r.file_path.name}  ({len(r.errors)} err)")
    if warned and args.strict:
        print(f"严格模式：{len(warned)} 个文件因告警被视为失败")

    if failed:
        return 1
    if args.strict and warned:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
