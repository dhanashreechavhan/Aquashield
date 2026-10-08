from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import networkx as nx

from src.data_store import load_road_dataset


def _risk_factor(score: float) -> float:
    return 1.0 + (float(score) / 50.0)


def build_route_graph(roads: pd.DataFrame | None = None, k: int = 12, max_km: float = 2.0) -> nx.Graph:
    roads = load_road_dataset() if roads is None else roads
    coords = roads[["mid_lat", "mid_lon"]].to_numpy(dtype=float)
    tree = cKDTree(coords)
    G = nx.Graph()
    for i, row in roads.iterrows():
        G.add_node(
            int(i),
            lat=float(row.mid_lat),
            lon=float(row.mid_lon),
            infra_risk=row.infra_risk,
            infra_risk_score=float(row.infra_risk_score),
            name=str(row.name),
            highway=str(row.highway),
        )
    dist_deg, idx = tree.query(coords, k=min(k + 1, len(coords)))
    max_deg = max_km / 111.0
    scores = roads["infra_risk_score"].to_numpy(dtype=float)
    for i, neighbours in enumerate(idx):
        for j, d in zip(neighbours[1:], dist_deg[i][1:]):
            j = int(j)
            if d > max_deg or i == j:
                continue
            km = float(d) * 111.0
            avg_score = (scores[i] + scores[j]) / 2.0
            G.add_edge(
                int(i),
                j,
                dist_km=km,
                risk_weight=km * _risk_factor(avg_score),
                avg_infra_score=float(avg_score),
            )
    if G.number_of_edges() == 0:
        return G
    largest = max(nx.connected_components(G), key=len)
    return G.subgraph(largest).copy()


def nearest_node(G: nx.Graph, lat: float, lon: float) -> int:
    nodes = np.array([[G.nodes[n]["lat"], G.nodes[n]["lon"]] for n in G.nodes])
    ids = np.array(list(G.nodes))
    d = (nodes[:, 0] - lat) ** 2 + (nodes[:, 1] - lon) ** 2
    return int(ids[int(np.argmin(d))])


def apply_community_penalties(
    G: nx.Graph,
    reports: list[dict],
    radius_km: float = 0.45,
    max_extra: float = 2.5,
) -> nx.Graph:
    """Increase edge weights near verified, recent user reports. Demo posts are ignored."""
    H = G.copy()
    now = pd.Timestamp.now(tz="UTC")
    usable = []
    for rep in reports:
        if rep.get("source_layer") != "user_report":
            continue
        if rep.get("verification_status") != "Verified":
            continue
        if rep.get("latitude") is None or rep.get("longitude") is None:
            continue
        ts = pd.Timestamp(rep["created_at"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        age_hours = (now - ts.tz_convert("UTC")).total_seconds() / 3600.0
        if age_hours > 48:
            continue
        usable.append((float(rep["latitude"]), float(rep["longitude"]), age_hours))
    if not usable:
        return H
    for u, v, data in H.edges(data=True):
        mid_lat = (H.nodes[u]["lat"] + H.nodes[v]["lat"]) / 2
        mid_lon = (H.nodes[u]["lon"] + H.nodes[v]["lon"]) / 2
        extra = 1.0
        for lat, lon, age in usable:
            dist = np.hypot(mid_lat - lat, mid_lon - lon) * 111.0
            if dist <= radius_km:
                freshness = max(0.25, 1.0 - age / 48.0)
                extra = max(extra, 1.0 + max_extra * freshness * (1.0 - dist / radius_km))
        data["risk_weight"] = data["dist_km"] * extra * (1.0 + data.get("avg_infra_score", 0) / 50.0)
        data["community_multiplier"] = extra
    return H


def shortest_path(G: nx.Graph, start: int, end: int, weight: str = "risk_weight") -> dict:
    path = nx.shortest_path(G, start, end, weight=weight)
    coords = [(G.nodes[n]["lat"], G.nodes[n]["lon"]) for n in path]
    dist = 0.0
    risk_acc = 0.0
    high_edges = 0
    for a, b in zip(path[:-1], path[1:]):
        ed = G.edges[a, b]
        dist += ed.get("dist_km", 0)
        risk_acc += ed.get("avg_infra_score", 0)
        if ed.get("avg_infra_score", 0) >= 60:
            high_edges += 1
    n_edges = max(len(path) - 1, 1)
    return {
        "nodes": path,
        "coords": coords,
        "distance_km": dist,
        "mean_infra_score": risk_acc / n_edges,
        "high_risk_edges": high_edges,
        "weight_key": weight,
    }
