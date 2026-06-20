"""主题关联分析：构建实体/主题共现网络。"""

from collections import defaultdict
from typing import Any, Dict, List, Set

from kb.models import Entity, Relation, Report


def _normalize(name: str) -> str:
    return " ".join(name.lower().split())


def build_topic_graph(
    reports: List[Report],
    min_edge_weight: int = 1,
    top_n_nodes: int = 100,
) -> Dict[str, Any]:
    """基于实体共现构建主题关联图。"""
    node_counts: Dict[str, int] = defaultdict(int)
    edge_counts: Dict[tuple, int] = defaultdict(int)
    edge_reports: Dict[tuple, Set[str]] = defaultdict(set)

    for report in reports:
        entity_names = [_normalize(e.name) for e in report.entities]
        entity_names = list(set(entity_names))

        for name in entity_names:
            node_counts[name] += 1

        # 同一报告内实体两两共现
        for i in range(len(entity_names)):
            for j in range(i + 1, len(entity_names)):
                a, b = entity_names[i], entity_names[j]
                if a == b:
                    continue
                key = tuple(sorted((a, b)))
                edge_counts[key] += 1
                edge_reports[key].add(report.id)

    # 取 top N 节点
    sorted_nodes = sorted(node_counts.items(), key=lambda x: x[1], reverse=True)
    top_nodes = {name for name, _ in sorted_nodes[:top_n_nodes]}

    # 过滤边
    links: List[Dict[str, Any]] = []
    for (a, b), weight in edge_counts.items():
        if a not in top_nodes or b not in top_nodes:
            continue
        if weight < min_edge_weight:
            continue
        links.append(
            {
                "source": a,
                "target": b,
                "weight": weight,
                "report_ids": list(edge_reports[(a, b)]),
            }
        )

    nodes: List[Dict[str, Any]] = [
        {
            "id": name,
            "name": name,
            "value": count,
        }
        for name, count in sorted_nodes
        if name in top_nodes
    ]

    return {
        "nodes": nodes,
        "links": links,
    }


def merge_entities(global_entities: Dict[str, Entity], report: Report) -> None:
    """将报告中的实体合并到全局实体索引。"""
    for entity in report.entities:
        key = _normalize(entity.name)
        if key in global_entities:
            global_entities[key].count += entity.count
            if report.id not in global_entities[key].report_ids:
                global_entities[key].report_ids.append(report.id)
        else:
            global_entities[key] = Entity(
                id=entity.id,
                name=entity.name,
                report_ids=[report.id],
                count=entity.count,
            )


def merge_topics(global_topics: Dict[str, Any], report: Report) -> None:
    """将报告中的主题合并到全局主题索引。"""
    for topic in report.topics:
        key = _normalize(topic.name)
        if key in global_topics:
            global_topics[key]["count"] += topic.count
            if report.id not in global_topics[key]["report_ids"]:
                global_topics[key]["report_ids"].append(report.id)
        else:
            global_topics[key] = {
                "id": topic.id,
                "name": topic.name,
                "report_ids": [report.id],
                "count": topic.count,
            }
