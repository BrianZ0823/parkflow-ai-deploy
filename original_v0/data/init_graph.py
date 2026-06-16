# -*- coding: utf-8 -*-
"""初始化 NetworkX 产业链图谱"""
import networkx as nx
import json
import os
import sys

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

GRAPH_PATH = os.path.join(PROJECT_ROOT, "db", "industry_graph.json")


def build_graph() -> nx.DiGraph:
    """构建产业链有向图"""
    from data.seed_data.industry_graph import INDUSTRY_NODES, INDUSTRY_EDGES, CHAIN_GAPS

    G = nx.DiGraph()

    for name, attrs in INDUSTRY_NODES:
        G.add_node(name, **attrs)

    for src, dst, attrs in INDUSTRY_EDGES:
        G.add_edge(src, dst, **attrs)

    # 将缺口分析存为图属性
    G.graph["chain_gaps"] = CHAIN_GAPS

    return G


def save_graph(G: nx.DiGraph):
    """将图序列化为 JSON 文件"""
    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    data = nx.node_link_data(G, edges="links")
    # 附加 chain_gaps
    data["chain_gaps"] = G.graph.get("chain_gaps", {})
    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[NetworkX] 图谱已保存: {GRAPH_PATH}")
    print(f"  节点: {G.number_of_nodes()}, 边: {G.number_of_edges()}")


def load_graph() -> nx.DiGraph:
    """从 JSON 文件加载图"""
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    chain_gaps = data.pop("chain_gaps", {})
    G = nx.node_link_graph(data, directed=True, edges="links")
    G.graph["chain_gaps"] = chain_gaps
    return G


def init_graph():
    G = build_graph()
    save_graph(G)


if __name__ == "__main__":
    init_graph()
