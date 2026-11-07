#!/usr/bin/env python3
"""Paper/poster figures and tables from Week-5 run directories.

  w5figures.py project/runs/<run-a> [project/runs/<run-b> ...] -o paper/figures/week5

Each run directory needs manifest.yaml (validated by w5run.py) and, for the
timeline figure, incident-timeline.csv (w5run.py timeline). Writes:

  timeline-<run_id>.pdf/.png   one swim-lane per evidence source, minutes from scenario start
  phases.pdf/.png              detect / identify / contain / recover, one bar per run
  metrics.tex, metrics.md      the same numbers as a table (booktabs / Markdown)

Missing milestones are drawn as absent and written as "not reached", never imputed.
"""
import argparse
import csv
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import w5run  # noqa: E402

# Validated categorical slots 1-4 (light surface); low-contrast slots get relief
# from marker shapes, a legend and the table, never colour alone.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
LAYERS = {  # layer -> (colour, marker)
    "host": ("#2a78d6", "o"),
    "network": ("#eb6834", "s"),
    "application": ("#1baf7a", "^"),
    "platform": ("#eda100", "D"),
}
PHASES = [  # metric key, label, colour (fixed order)
    ("T_detect_s", "Detect", "#2a78d6"),
    ("T_identify_s", "Identify", "#eb6834"),
    ("T_contain_s", "Contain", "#1baf7a"),
    ("T_recover_s", "Recover", "#eda100"),
]
MILESTONES = [
    ("first_detection_utc", "first detection"),
    ("identified_utc", "identified"),
    ("contained_utc", "contained"),
    ("recovered_utc", "recovered"),
]


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.xaxis.label.set_color(INK2)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def load_run(run_dir):
    run_dir = pathlib.Path(run_dir)
    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text(encoding="utf-8"))
    rows = []
    tl = run_dir / "incident-timeline.csv"
    if tl.exists():
        rows = list(csv.DictReader(tl.read_text(encoding="utf-8").splitlines()))
    return manifest, rows


def minutes(utc, start):
    return (w5run.parse_utc(utc, "utc") - start).total_seconds() / 60


def timeline_figure(manifest, rows, out):
    start = w5run.parse_utc(manifest["window"]["start_utc"], "window.start_utc")
    sources = list(dict.fromkeys(r["source"] for r in rows))
    fig, ax = plt.subplots(figsize=(7.2, 0.55 * max(len(sources), 2) + 1.5), facecolor=SURFACE)
    style(ax)
    for layer, (colour, marker) in LAYERS.items():
        pts = [(minutes(r["utc"], start), sources.index(r["source"])) for r in rows if r["layer"] == layer]
        if pts:
            ax.scatter(*zip(*pts), s=64, c=colour, marker=marker, edgecolors=SURFACE, linewidths=2,
                       label=layer, zorder=3)
    ax.set_yticks(range(len(sources)), sources)
    ax.set_ylim(-0.6, len(sources) - 0.4)
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, linewidth=1, zorder=2)
    ax.text(0, -0.75, "scenario start", color=INK2, fontsize=7, ha="center", va="bottom")
    ms = manifest.get("milestones") or {}
    for key, label in MILESTONES:
        if ms.get(key):
            x = minutes(ms[key], start)
            ax.axvline(x, color=INK2, linewidth=1, linestyle=(0, (3, 3)), zorder=2)
            ax.text(x, -0.75, label, color=INK2, fontsize=7, ha="center", va="bottom")
    ax.set_xlabel("minutes from scenario start (UTC " + manifest["window"]["start_utc"] + ")", fontsize=8)
    ax.set_title(f"Incident timeline: {manifest['run_id']} ({manifest['team_role']})", loc="left",
                 fontsize=9, color=INK, pad=22)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.15), ncol=4, frameon=False, fontsize=8,
              labelcolor=INK2, handletextpad=0.3, columnspacing=1.2)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out / f"timeline-{manifest['run_id']}.{ext}", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fmt(seconds):
    if seconds is None:
        return "not reached"
    return f"{seconds / 60:.1f} min" if seconds >= 90 else f"{seconds:.0f} s"


def phases_figure(metrics, out):
    fig, ax = plt.subplots(figsize=(7.2, 0.6 * len(metrics) + 1.4), facecolor=SURFACE)
    style(ax)
    total = max([sum(m[k] or 0 for k, _, _ in PHASES) for m in metrics] + [1]) / 60
    for row, m in enumerate(metrics):
        left = 0.0
        for key, label, colour in PHASES:
            v = m[key]
            if v is None:
                continue
            width = v / 60
            ax.barh(row, width, left=left, height=0.5, color=colour, edgecolor=SURFACE, linewidth=2)
            if width > total * 0.12:
                ax.text(left + width / 2, row, fmt(v), ha="center", va="center", fontsize=7, color=INK)
            left += width
        missing = [label for key, label, _ in PHASES if m[key] is None]
        if missing:
            ax.text(left + total * 0.01, row, "not reached: " + ", ".join(missing).lower(),
                    va="center", fontsize=7, color=INK2)
    ax.set_yticks(range(len(metrics)), [f"{m['run_id']}\n({m['team_role']})" for m in metrics], fontsize=7)
    ax.set_ylim(len(metrics) - 0.4, -0.6)  # fixed bar thickness, first run on top
    ax.set_xlim(0, total * 1.35)
    ax.set_xlabel("minutes from scenario start", fontsize=8)
    ax.set_title("Detection and response phases per run", loc="left", fontsize=9, color=INK, pad=26)
    # One fixed-order legend entry per phase, whether or not a run reached it.
    handles = [Patch(facecolor=colour, label=label) for _, label, colour in PHASES]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, frameon=False,
              fontsize=8, labelcolor=INK2, borderaxespad=0.3)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(out / f"phases.{ext}", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def tables(metrics, out):
    head = ["Run", "Role", "T_detect", "T_identify", "T_contain", "T_recover", "Detections", "FP", "FN", "Gaps"]
    rows = [[m["run_id"], m["team_role"], *(fmt(m[k]) for k, _, _ in PHASES),
             str(m["detections"]), str(m["false_positives"]), str(m["false_negatives"]), str(m["evidence_gaps"])]
            for m in metrics]
    md = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    (out / "metrics.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    esc = lambda s: s.replace("_", r"\_")  # noqa: E731
    tex = [r"\begin{tabular}{llrrrrrrrr}", r"\toprule", " & ".join(esc(h) for h in head) + r" \\", r"\midrule"]
    tex += [" & ".join(esc(c) for c in r) + r" \\" for r in rows]
    tex += [r"\bottomrule", r"\end{tabular}"]
    (out / "metrics.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    metrics = []
    for run in a.runs:
        manifest, rows = load_run(run)
        metrics.append(w5run.metrics(manifest))
        if rows:
            timeline_figure(manifest, rows, out)
    phases_figure(metrics, out)
    tables(metrics, out)
    print(f"{len(metrics)} run(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
