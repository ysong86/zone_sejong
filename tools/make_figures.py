# -*- coding: utf-8 -*-
"""보고서용 그림 두 장 — data/latest.json(실측)에서 그린다.

  fig1_svc_map.png   행복도시 행정동별 15분 생활서비스 + 생활권 경계
  fig2_lq_bar.png    생활권별 계획기능 특화도(LQ)
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import livingzone as LZ  # noqa: E402

OUT = os.path.join(HERE, "docs", "figures")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
RAMP = ["#C9DCE4", "#94BCCD", "#5A95B2", "#2C6E8F", "#123F57"]
INK = "#15232A"


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def fig1(latest):
    units = {u["name"]: u for u in load("assets/sejong_units.json")["units"]}
    zones = load("assets/sejong_zones.json")["zones"]
    zc = {z["id"]: z["color"] for z in LZ.ZONES}
    vals = {n: latest["units"].get(n, {}).get("svc") for n in units}
    bins = [5.0, 6.0, 7.0, 7.8]          # 5단계 경계(종/8)

    def color(v):
        if v is None:
            return "#EEF0EE"
        k = sum(v >= b for b in bins)
        return RAMP[k]

    fig, ax = plt.subplots(figsize=(6.6, 4.9), dpi=200)
    kx = 0.8036
    for n, u in units.items():
        for ring in u["rings"]:
            ax.add_patch(MplPolygon([(x * kx, y) for x, y in ring], closed=True,
                                    facecolor=color(vals[n]), edgecolor="white", linewidth=0.6))
    for z in zones:
        for ring in z["rings"]:
            ax.add_patch(MplPolygon([(x * kx, y) for x, y in ring], closed=True, fill=False,
                                    edgecolor=zc[z["id"]], linewidth=1.8))
    for n, u in units.items():
        x, y = u["label"]
        if 127.215 < x < 127.365 and 36.455 < y < 36.552 and n != "세종동":
            v = vals[n]
            ax.text(x * kx, y, f"{n}\n{v:.1f}" if v is not None else n, ha="center", va="center",
                    fontsize=6.2, color=INK if (v or 0) < 7 else "white", linespacing=1.1)
    for z in zones:
        if z["id"] in "123456S":
            x, y = z["label"]
            name = next(q["name"] for q in LZ.ZONES if q["id"] == z["id"])
            dy = {"S": -0.006, "6": 0.004}.get(z["id"], 0.0)
            ax.text(x * kx, y + dy, name, ha="center", va="center", fontsize=7.4, fontweight="bold",
                    color=zc[z["id"]],
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    ax.set_xlim(127.215 * kx, 127.365 * kx)
    ax.set_ylim(36.455, 36.552)
    ax.set_aspect("equal")
    ax.axis("off")
    labels = ["5.0 미만", "5.0~6.0", "6.0~7.0", "7.0~7.8", "7.8 이상"]
    handles = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in RAMP]
    ax.legend(handles, labels, title="15분 생활서비스(종/8)", loc="lower right", fontsize=6.5,
              title_fontsize=7, frameon=True, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_svc_map.png"), bbox_inches="tight")
    plt.close(fig)


def fig2(latest):
    lq, floor = latest["lq"], latest["floor"]
    rows = [(z["id"], z["name"], LZ.FUNCTIONS[LZ.PLANNED[z["id"]]]) for z in LZ.ZONES if z["id"] in LZ.PLANNED]
    names = [f"{n}\n({f})" for _, n, f in rows]
    vals = [(lq.get(i) or [0] * 6)[LZ.PLANNED[i]] for i, _, _ in rows]
    cols = [next(z["color"] for z in LZ.ZONES if z["id"] == i) for i, _, _ in rows]
    fig, ax = plt.subplots(figsize=(4.6, 3.55), dpi=220)
    bars = ax.bar(range(len(rows)), vals, color=cols, width=0.62)
    ax.axhline(1.0, color="#7C8A8F", linestyle="--", linewidth=0.9)
    ax.text(len(rows) - 0.45, 1.08, "세종 평균 = 1.0", fontsize=7, color="#4B5B62", ha="right")
    for b, v, (i, _, _) in zip(bars, vals, rows):
        note = "*" if floor.get(i, {}).get("thin") else ""
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.2f}{note}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(names, fontsize=6.6)
    ax.set_ylabel("계획기능 특화도(LQ)", fontsize=8)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.set_ylim(0, max(vals) * 1.18)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#E6EBE8", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2_lq_bar.png"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    latest = load("data/latest.json")
    fig1(latest)
    fig2(latest)
    print("저장:", OUT)
