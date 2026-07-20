"""Eval harness: 15 questions x 4 retrieval ablations (spec Day 3, 3:30-4:30).

Run:  py scripts/eval.py            full suite (~10 min, 60 LLM calls)
      py scripts/eval.py --quick    full mode only (15 calls)

Modes: full (hybrid+graph) | dense (no BM25) | bm25 (no dense) | no_graph.
A case passes when the abstain decision matches expectation AND, for answerable
questions, at least one expected source appears in the citations actually used.

Outputs: scripts/eval_results.json + static/eval.html (ablation bar chart).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
import ask as ask_mod

CASES = [
    {"q": "P-101A keeps tripping on high vibration - has this happened before?",
     "abstain": False, "cite_any": ["P-101A"]},
    {"q": "How often should the suction strainers on the P-101 pumps be cleaned?",
     "abstain": False, "cite_any": ["SOP-114"]},
    {"q": "What is the procedure for replacing a mechanical seal on a process pump?",
     "abstain": False, "cite_any": ["SOP-103"]},
    {"q": "Which pumps share the same class as P-101A and what failures have they had?",
     "abstain": False, "cite_any": ["P-101A", "P-101B", "P-101C"]},
    {"q": "What safety precautions apply before opening a heat exchanger?",
     "abstain": False, "cite_any": ["SOP-105"]},
    {"q": "The pump will not build discharge pressure after starting - what should I check?",
     "abstain": False, "cite_any": ["SOP-101", "SOP-114"]},
    {"q": "How much downtime have seal failures caused on P-101A?",
     "abstain": False, "cite_any": ["P-101A"]},
    {"q": "How do I verify a control valve positioner is calibrated correctly?",
     "abstain": False, "cite_any": ["SOP-108"]},
    {"q": "What does lock-out tag-out require before intrusive work can start?",
     "abstain": False, "cite_any": ["SOP-118"]},
    {"q": "Has HX-202A had fouling or overheating problems?",
     "abstain": False, "cite_any": ["HX-202A", "SOP-105", "SOP-116"]},
    {"q": "What vibration level requires the machine to be shut down?",
     "abstain": False, "cite_any": ["SOP-110"]},
    {"q": "What happened the last time a plugged strainer tripped P-101A?",
     "abstain": False, "cite_any": ["P-101A", "SOP-114"]},
    {"q": "What is the boiler feedwater treatment procedure?", "abstain": True},
    {"q": "What is the turbine lube oil specification?", "abstain": True},
    {"q": "Who is the plant manager of Plant Site A?", "abstain": True},
]

MODES = ["full", "dense", "bm25", "no_graph"]


def cited_sources(result):
    out = []
    for c in result.get("citations", []):
        for key in ("doc", "tag", "chunk_id", "label"):
            if c.get(key):
                out.append(str(c[key]))
    return " | ".join(out)


def run_case(case, mode):
    t0 = time.time()
    r = ask_mod.ask(case["q"], mode=mode)
    hit = True
    if case["abstain"]:
        hit = r["abstained"]
    else:
        if r["abstained"]:
            hit = False
        else:
            sources = cited_sources(r)
            hit = any(k in sources for k in case["cite_any"])
    return {"q": case["q"], "mode": mode, "pass": hit,
            "abstained": r["abstained"], "confidence": r["confidence"],
            "elapsed_s": round(time.time() - t0, 1),
            "cited": cited_sources(r)[:200]}


def bar_chart_html(summary):
    rows = ""
    for mode in MODES:
        if mode not in summary:
            continue
        s = summary[mode]
        pct = round(100 * s["passed"] / s["total"])
        rows += (
            f'<div class="row"><span class="lbl">{mode}</span>'
            f'<div class="bar"><i style="width:{pct}%"></i></div>'
            f'<span class="val">{s["passed"]}/{s["total"]} ({pct}%) · '
            f'{s["mean_latency"]}s avg</span></div>\n')
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Plant Brain — retrieval ablation</title><style>
 body{{background:#0d1117;color:#e6edf3;font:14px "Segoe UI",sans-serif;
      max-width:760px;margin:40px auto;padding:0 20px}}
 h1{{font-size:18px}} .sub{{color:#8b949e;font-size:12px;margin-bottom:24px}}
 .row{{display:flex;align-items:center;gap:12px;margin:14px 0}}
 .lbl{{width:80px;text-align:right;color:#8b949e}}
 .bar{{flex:1;height:26px;background:#21262d;border-radius:6px;overflow:hidden}}
 .bar i{{display:block;height:100%;background:linear-gradient(90deg,#1f6feb,#4da3ff)}}
 .val{{width:190px;font-size:12px;color:#8b949e}}
</style></head><body>
<h1>Retrieval ablation — 15-question eval</h1>
<div class="sub">pass = correct abstain decision + expected source in used citations ·
hybrid BM25+dense+graph vs each leg removed</div>
{rows}</body></html>"""


def main():
    modes = ["full"] if "--quick" in sys.argv else MODES
    results, summary = [], {}
    for mode in modes:
        mode_results = []
        for i, case in enumerate(CASES, 1):
            r = run_case(case, mode)
            mode_results.append(r)
            print(f"[{mode} {i:2d}/{len(CASES)}] "
                  f"{'PASS' if r['pass'] else 'FAIL'} conf={r['confidence']} "
                  f"{r['elapsed_s']}s  {case['q'][:60]}")
        passed = sum(1 for r in mode_results if r["pass"])
        summary[mode] = {
            "passed": passed, "total": len(CASES),
            "mean_latency": round(sum(r["elapsed_s"] for r in mode_results)
                                  / len(mode_results), 1)}
        results.extend(mode_results)
        print(f"== {mode}: {passed}/{len(CASES)} passed, "
              f"{summary[mode]['mean_latency']}s mean ==\n")

    out = Path(__file__).parent / "eval_results.json"
    out.write_text(json.dumps({"summary": summary, "results": results}, indent=1),
                   encoding="utf-8")
    chart = Path(__file__).parent.parent / "static" / "eval.html"
    chart.write_text(bar_chart_html(summary), encoding="utf-8")
    print(f"wrote {out} and {chart}")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
