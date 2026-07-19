"""Plant Brain corpus generator — seeded, deterministic (spec section 6).

Regenerate any time with:  py datagen/generate_corpus.py
Never hand-edit files in corpus/ — change this script and regenerate.

Outputs (spec 6.10):
    corpus/equipment_register.xlsx
    corpus/work_orders.xlsx
    corpus/inspection_records.xlsx
    corpus/procedures/SOP-*.pdf
    corpus/audio/            (user-recorded clips go here; see docs/voice_recording_scripts.md)

Planted patterns (spec 6.5) — verified by assertions at the end of this script:
    1. Overdue:   P-101A, 4x SER at 88/84/86-day gaps, last one DEMO_DATE-80d  -> risk ~0.93
    2. Siblings:  PLU on P-101A/B/C only; P-102A, P-102B, P-103A clean of PLU
    3. Chronic:   P-102A, 4x VIB inside the last 12 months
    4. Divergence: SOP-114 says monthly strainer cleaning (voice clips say fortnightly in monsoon)

Injected messiness (spec 6.6):
    "P-101A" in work orders, "Pump 101A" in procedures, "P101-A" in one inspection
    record ("p-101a" belongs to a voice transcript, recorded by the user).
    Dates: YYYY-MM-DD in work_orders.xlsx, DD/MM/YYYY in inspection_records.xlsx.
    One failure code deliberately mistyped ("LKE" for LEK) on a random corrective WO.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

sys.path.insert(0, str(Path(__file__).parent))
from sop_content import SOPS

# ----------------------------------------------------------------------------- config
DEMO_DATE = date(2026, 7, 22)   # adjust to the actual demo day, then regenerate
SEED = 8                        # PS-8
ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"

rng = random.Random(SEED)

# ----------------------------------------------------------------------------- reference data
EQUIPMENT = [
    # tag, iso14224 class, area, criticality, service
    ("P-101A",  "centrifugal_pump", "Area-1", "high",   "Process feed transfer pump (duty)"),
    ("P-101B",  "centrifugal_pump", "Area-1", "high",   "Process feed transfer pump (standby)"),
    ("P-101C",  "centrifugal_pump", "Area-1", "medium", "Process feed transfer pump (spare)"),
    ("P-102A",  "centrifugal_pump", "Area-2", "high",   "Cooling water circulation pump (duty)"),
    ("P-102B",  "centrifugal_pump", "Area-2", "medium", "Cooling water circulation pump (standby)"),
    ("P-103A",  "centrifugal_pump", "Area-2", "low",    "Auxiliary cooling water pump"),
    ("HX-201A", "heat_exchanger",   "Area-1", "high",   "Feed/effluent interchanger"),
    ("HX-201B", "heat_exchanger",   "Area-1", "medium", "Product trim cooler"),
    ("HX-202A", "heat_exchanger",   "Area-2", "low",    "Cooling water return exchanger"),
    ("CV-301A", "control_valve",    "Area-1", "medium", "Feed flow control valve"),
    ("CV-302A", "control_valve",    "Area-1", "low",    "Product pressure control valve"),
    ("CV-303A", "control_valve",    "Area-2", "low",    "Cooling water basin makeup valve"),
]
PUMPS = [e[0] for e in EQUIPMENT if e[1] == "centrifugal_pump"]

FAILURE_MODES = {
    "SER": "Seal leakage",
    "VIB": "Excessive vibration",
    "BRG": "Bearing failure",
    "PLU": "Plugged / choked",
    "LEK": "External leakage",
    "OHE": "Overheating",
    "ELP": "Electrical problem",
}

DOWNTIME = {  # corrective downtime hours by mode (spec 6.4)
    "SER": (4, 8), "VIB": (6, 12), "BRG": (16, 40), "PLU": (2, 4),
    "LEK": (3, 8), "OHE": (8, 16), "ELP": (2, 6),
}

TECHS = ["R. Kumar", "S. Iyer", "A. Sharma", "M. Patel",
         "V. Reddy", "J. Fernandes", "K. Nair", "D. Singh"]

CORRECTIVE_DESC = {
    "SER": ["Mechanical seal leaking at drive end. Replaced seal cartridge per SOP-103 and flushed seal pot.",
            "Seal weep worsened to steady drip. Fitted new cartridge seal, corrected seal chamber run-out."],
    "VIB": ["High vibration reported on route reading, zone C. Balanced impeller and corrected coupling alignment.",
            "Vibration alarm at DE bearing. Spectrum showed misalignment; realigned and rechecked per SOP-110."],
    "BRG": ["DE bearing failed with audible rumble. Replaced both bearings, cleaned housing, renewed oil.",
            "Bearing seizure on start. Replaced bearing set, checked shaft journal, realigned driver."],
    "PLU": ["Tripped on low suction pressure. Suction strainer found heavily plugged; cleaned element per SOP-114.",
            "Low discharge flow. Strainer element choked with debris; cleaned and refitted per SOP-114."],
    "LEK": ["Flange leak at discharge joint. Renewed gasket and retorqued to bolting table.",
            "Casing drain plug weeping. Resealed plug and confirmed leak-free at operating pressure."],
    "OHE": ["High bearing housing temperature. Restored cooling water flow and flushed cooler lines.",
            "Approach temperature rising; unit fouled. Cleaned per SOP-105 and restored performance."],
    "ELP": ["Motor tripping on overload. Found loose terminal connection; remade and retested.",
            "Intermittent trip on start. Megger test on motor windings passed; replaced faulty contactor."],
}

PREVENTIVE_DESC = {
    "centrifugal_pump": ["Scheduled lubrication and vibration route reading per SOP-110.",
                         "Alignment check and coupling inspection.",
                         "Cleaned suction strainer per SOP-114 monthly schedule."],
    "heat_exchanger":   ["Scheduled backflush and performance reading per SOP-105.",
                         "Gasket joint survey and thermal performance check."],
    "control_valve":    ["Stroke test and positioner check per SOP-108.",
                         "Packing gland inspection and air set filter service."],
}

INSPECTION_DESC = ["Routine thermography survey completed, no anomaly.",
                   "Ultrasonic thickness survey at CMLs, readings within limits.",
                   "Visual and NDE inspection completed per schedule."]


def d(days_before_demo: int) -> date:
    return DEMO_DATE - timedelta(days=days_before_demo)


# ----------------------------------------------------------------------------- work orders
def build_work_orders():
    wos = []  # dicts: tag, date, type, code, downtime, desc, tech

    def add(tag, when, wtype, code=None, downtime=0.0, desc="", tech=None):
        wos.append({"tag": tag, "date": when, "type": wtype, "code": code,
                    "downtime": round(downtime, 1), "desc": desc,
                    "tech": tech or rng.choice(TECHS)})

    # --- Pattern 1: P-101A overdue on SER. Intervals 88, 84, 86; last at demo-80.
    ser_dates = [d(80)]
    for gap in (86, 84, 88):                      # walk back in time
        ser_dates.append(ser_dates[-1] - timedelta(days=gap))
    for i, when in enumerate(sorted(ser_dates)):
        add("P-101A", when, "corrective", "SER",
            rng.uniform(*DOWNTIME["SER"]), CORRECTIVE_DESC["SER"][i % 2])

    # --- Pattern 2: PLU on P-101A/B/C only (single events -> no accidental MTBF alerts).
    add("P-101A", d(30), "corrective", "PLU", rng.uniform(*DOWNTIME["PLU"]),
        "Tripped on low suction pressure. Suction strainer found heavily plugged with "
        "monsoon debris; cleaned element per SOP-114.")
    add("P-101B", d(300), "corrective", "PLU", rng.uniform(*DOWNTIME["PLU"]),
        CORRECTIVE_DESC["PLU"][1])
    add("P-101C", d(500), "corrective", "PLU", rng.uniform(*DOWNTIME["PLU"]),
        CORRECTIVE_DESC["PLU"][0])

    # --- Pattern 3: P-102A chronic VIB, four events inside 12 months.
    for days in (20, 120, 230, 330):
        add("P-102A", d(days), "corrective", "VIB",
            rng.uniform(*DOWNTIME["VIB"]),
            "Repeat high vibration on DE bearing, zone C on route. Realigned and "
            "returned to service; root cause not established.")

    # --- Random correctives: one per (equipment, mode), protected combos excluded.
    protected = {("P-101A", "SER"), ("P-101A", "PLU"), ("P-101B", "PLU"),
                 ("P-101C", "PLU"), ("P-102A", "VIB"),
                 ("P-102A", "PLU"), ("P-102B", "PLU"), ("P-103A", "PLU")}  # P-102/103 stay PLU-free
    pump_only = {"SER", "PLU"}          # seal/strainer modes make no sense on HX/CV
    combos = []
    for tag, klass, *_ in EQUIPMENT:
        for code in FAILURE_MODES:
            if (tag, code) in protected:
                continue
            if code in pump_only and klass != "centrifugal_pump":
                continue
            if code == "VIB" and klass == "control_valve":
                continue
            combos.append((tag, code))
    rng.shuffle(combos)
    lek_combos = [c for c in combos if c[1] == "LEK"]
    chosen = combos[:29]
    if not any(c[1] == "LEK" for c in chosen):    # guarantee a LEK WO for the typo
        chosen[-1] = lek_combos[0]
    typo_done = False
    for tag, code in chosen:
        written_code = code
        if code == "LEK" and not typo_done:       # spec 6.6: one deliberate typo
            written_code, typo_done = "LKE", True
        add(tag, d(rng.randint(90, 1050)), "corrective", written_code,
            rng.uniform(*DOWNTIME[code]), rng.choice(CORRECTIVE_DESC[code]))

    # --- Preventives: interval by criticality across the 3-year span.
    interval = {"high": 150, "medium": 220, "low": 350}
    for tag, klass, _area, crit, _svc in EQUIPMENT:
        days = rng.randint(20, 80)
        while days < 1095:
            add(tag, d(days), "preventive", None, rng.uniform(0.5, 3.0),
                rng.choice(PREVENTIVE_DESC[klass]))
            days += interval[crit] + rng.randint(-15, 15)

    # --- Inspection-type WOs.
    for _ in range(18):
        tag = rng.choice([e[0] for e in EQUIPMENT])
        add(tag, d(rng.randint(30, 1060)), "inspection", None, 0.0,
            rng.choice(INSPECTION_DESC))

    # --- IDs, chronological order.
    wos.sort(key=lambda w: w["date"])
    for i, w in enumerate(wos, 1):
        w["wo_id"] = f"WO-{w['date'].year}-{i:04d}"
    return wos


# ----------------------------------------------------------------------------- xlsx writers
def write_xlsx(path, header, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(r)
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col) + 2
        ws.column_dimensions[col[0].column_letter].width = min(width, 90)
    wb.save(path)


def build_inspections():
    # DD/MM/YYYY here (spec 6.6); two records deliberately expired; one "P101-A" spelling.
    def dmy(dt):
        return dt.strftime("%d/%m/%Y")
    rows = [
        ("IR-001", "HX-201A", dmy(d(200)), "No significant fouling; tube sample satisfactory", dmy(d(-165))),
        ("IR-002", "P101-A",  dmy(d(150)), "Vibration and thickness readings within limits",   dmy(d(-215))),
        ("IR-003", "CV-301A", dmy(d(420)), "Stroke test passed; hysteresis 1.4 percent",       dmy(d(55))),   # expired
        ("IR-004", "HX-202A", dmy(d(510)), "Moderate fouling noted; cleaning recommended",     dmy(d(145))),  # expired
        ("IR-005", "P-102A",  dmy(d(90)),  "Route vibration elevated, zone C; monitoring",     dmy(d(-275))),
        ("IR-006", "CV-303A", dmy(d(120)), "Valve passing slightly at seat; acceptable",       dmy(d(-245))),
    ]
    return rows


# ----------------------------------------------------------------------------- PDF renderer
def render_sops(outdir: Path):
    styles = getSampleStyleSheet()
    h_style = ParagraphStyle("SOPHead", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("SOPBody", parent=styles["Normal"], fontSize=10.5, leading=15, spaceAfter=6)
    word_counts = {}
    for sop in SOPS:
        path = outdir / f"{sop['sop_id']}.pdf"
        doc = SimpleDocTemplate(str(path), pagesize=A4,
                                leftMargin=2 * cm, rightMargin=2 * cm,
                                topMargin=2 * cm, bottomMargin=2 * cm,
                                title=f"{sop['sop_id']} {sop['title']}")
        story = [
            Paragraph(f"{sop['sop_id']} — {sop['title']}", styles["Title"]),
            Paragraph(f"Plant Site A · {sop['revision']} · Issued {sop['rev_date']} · "
                      f"Approved by Plant Engineering", styles["Italic"]),
            Spacer(1, 12),
        ]
        words = len(sop["title"].split())
        for si, (heading, blocks) in enumerate(sop["sections"], 1):
            story.append(Paragraph(f"{si}. {heading}", h_style))
            numbered = heading.lower().startswith("procedure")
            for bi, text in enumerate(blocks, 1):
                prefix = f"{si}.{bi}  " if numbered else ""
                story.append(Paragraph(prefix + text, body))
                words += len(text.split())
        doc.build(story)
        word_counts[sop["sop_id"]] = words
    return word_counts


# ----------------------------------------------------------------------------- verification
def verify(wos, word_counts):
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    # Pattern 1
    ser = sorted(w["date"] for w in wos if w["tag"] == "P-101A" and w["code"] == "SER")
    gaps = [(b - a).days for a, b in zip(ser, ser[1:])]
    check(len(ser) == 4 and gaps == [88, 84, 86], f"P1: SER gaps wrong: {gaps}")
    mtbf = sum(gaps) / len(gaps) if gaps else 0
    since = (DEMO_DATE - ser[-1]).days if ser else 0
    risk = since / mtbf if mtbf else 0
    check(0.8 < risk < 1.0, f"P1: risk ratio {risk:.2f} not in (0.8, 1.0)")

    # Pattern 2
    plu = {w["tag"] for w in wos if w["code"] == "PLU"}
    check(plu == {"P-101A", "P-101B", "P-101C"}, f"P2: PLU tags wrong: {plu}")

    # Pattern 3
    vib = [w for w in wos if w["tag"] == "P-102A" and w["code"] == "VIB"]
    recent = [w for w in vib if (DEMO_DATE - w["date"]).days <= 365]
    check(len(recent) == 4, f"P3: {len(recent)} VIB on P-102A in 12mo, want 4")

    # No accidental overdue/chronic on non-planted combos
    from collections import defaultdict
    by_combo = defaultdict(list)
    for w in wos:
        if w["type"] == "corrective" and w["code"] in FAILURE_MODES:
            by_combo[(w["tag"], w["code"])].append(w["date"])
    for (tag, code), dates in by_combo.items():
        if (tag, code) in {("P-101A", "SER"), ("P-102A", "VIB")}:
            continue
        dates.sort()
        g = [(b - a).days for a, b in zip(dates, dates[1:])]
        if g:
            r = (DEMO_DATE - dates[-1]).days / (sum(g) / len(g))
            check(r < 0.8, f"accidental overdue on {tag}/{code}: risk {r:.2f}")
        in12 = [x for x in dates if (DEMO_DATE - x).days <= 365]
        check(len(in12) < 3, f"accidental chronic on {tag}/{code}")

    # Messiness
    check(sum(1 for w in wos if w["code"] == "LKE") == 1, "expected exactly one LKE typo")
    check(all(w["code"] in FAILURE_MODES or w["code"] in (None, "LKE") for w in wos),
          "unknown failure code present")

    # Pattern 4 anchor + procedure word counts + alias forms
    sop114 = next(s for s in SOPS if s["sop_id"] == "SOP-114")
    flat = " ".join(t for _h, blocks in sop114["sections"] for t in blocks)
    check("monthly intervals" in flat and "Pump 101A" in flat,
          "P4: SOP-114 missing monthly statement or Pump 101A alias")
    for sid, wc in word_counts.items():
        check(800 <= wc <= 1200, f"{sid} word count {wc} outside 800-1200")

    # Volume
    check(110 <= len(wos) <= 130, f"WO count {len(wos)} outside 110-130")
    return fails


# ----------------------------------------------------------------------------- main
def main():
    (CORPUS / "procedures").mkdir(parents=True, exist_ok=True)
    (CORPUS / "audio").mkdir(exist_ok=True)

    write_xlsx(CORPUS / "equipment_register.xlsx",
               ["tag", "iso14224_class", "area", "criticality", "service"],
               [list(e) for e in EQUIPMENT])

    wos = build_work_orders()
    write_xlsx(CORPUS / "work_orders.xlsx",
               ["wo_id", "equipment_tag", "date", "type", "failure_code",
                "downtime_hrs", "description", "technician"],
               [[w["wo_id"], w["tag"], w["date"].strftime("%Y-%m-%d"), w["type"],
                 w["code"] or "", w["downtime"], w["desc"], w["tech"]] for w in wos])

    write_xlsx(CORPUS / "inspection_records.xlsx",
               ["record_id", "equipment_tag", "inspection_date", "result", "valid_until"],
               build_inspections())

    word_counts = render_sops(CORPUS / "procedures")

    fails = verify(wos, word_counts)

    n_types = {t: sum(1 for w in wos if w["type"] == t)
               for t in ("preventive", "corrective", "inspection")}
    print(f"demo date        : {DEMO_DATE}")
    print(f"work orders      : {len(wos)}  {n_types}")
    print(f"inspections file : 6 records (2 expired)")
    print(f"procedures       : {len(word_counts)} PDFs, words: {word_counts}")
    ser = sorted(w["date"] for w in wos if w["tag"] == "P-101A" and w["code"] == "SER")
    gaps = [(b - a).days for a, b in zip(ser, ser[1:])]
    print(f"P1 overdue       : SER gaps {gaps}, last {ser[-1]}, "
          f"risk {(DEMO_DATE - ser[-1]).days / (sum(gaps) / 3):.3f}")
    print(f"P2 siblings      : PLU on {sorted({w['tag'] for w in wos if w['code'] == 'PLU'})}")
    print(f"P3 chronic       : P-102A VIB dates "
          f"{[str(w['date']) for w in wos if w['tag'] == 'P-102A' and w['code'] == 'VIB']}")
    print(f"P4 divergence    : SOP-114 monthly statement present")
    if fails:
        print("\nVERIFICATION FAILURES:")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print("\nAll verification checks passed.")


if __name__ == "__main__":
    main()
