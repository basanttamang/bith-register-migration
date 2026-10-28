"""
Prove the migration is complete and correct.

Checks:
  A. Counts balance: source rows = migrated + rejected + held as duplicates
  B. Every source row is accounted for exactly once
  C. Content checksum: re-derive every migrated record from the source file
     using the same rules and compare with what is in the database
  D. Spot check: 20 random records written side by side for a person to read
  E. Detection: did the rules catch every problem planted in the test data?

Run after migrate.py:  python scripts/reconcile.py
"""
import csv, hashlib, json, os, random, sqlite3
from datetime import date
import rules

BASE = os.path.join(os.path.dirname(__file__), "..")
rows = list(csv.DictReader(open(os.path.join(BASE, "data", "legacy_birth_register.csv"), encoding="utf-8")))
key = json.load(open(os.path.join(BASE, "data", "injected_issues.json")))
db = sqlite3.connect(os.path.join(BASE, "output", "register.db"))
q = lambda sql: db.execute(sql).fetchall()
res = {}

# A. Counts
migrated = q("SELECT COUNT(*) FROM birth_registration")[0][0]
rejected = q("SELECT COUNT(*) FROM migration_reject")[0][0]
dups = q("SELECT COUNT(*) FROM duplicate_review")[0][0]
res["A_counts"] = {"source": len(rows), "migrated": migrated, "rejected": rejected, "duplicate_review": dups,
                   "balanced": len(rows) == migrated + rejected + dups}

# B. Each row exactly once
ids = [r[0] for r in q("SELECT source_row FROM birth_registration UNION ALL SELECT source_row FROM migration_reject "
                         "UNION ALL SELECT source_row FROM duplicate_review")]
res["B_each_row_once"] = {"rows_accounted": len(set(ids)), "rows_counted_twice": len(ids) - len(set(ids)),
                          "rows_missing": len(set(range(1, len(rows) + 1)) - set(ids)),
                          "pass": sorted(ids) == list(range(1, len(rows) + 1))}

# C. Content checksum
def expected(i):
    r = rows[i - 1]
    ad, cal, _ = rules.parse_date(r["dob"])
    return "|".join(map(str, [r["reg_no"], rules.clean_name(r["child_name"]), rules.parse_sex(r["sex"])[0], ad.isoformat(),
                              cal, rules.clean_name(r["father_name"]), rules.clean_name(r["mother_name"]),
                              rules.parse_ward(r["ward_no"])[0], rules.parse_phone(r["informant_phone"])[0]]))
actual = q("SELECT source_row, reg_no, child_name, sex, dob_ad, dob_calendar, father_name, mother_name, ward_no, "
           "informant_phone FROM birth_registration ORDER BY source_row")
h_exp, h_act, mismatches = hashlib.sha256(), hashlib.sha256(), 0
for row in actual:
    e, a = expected(row[0]), "|".join(map(str, row[1:]))
    h_exp.update(e.encode()); h_act.update(a.encode())
    mismatches += e != a
res["C_checksum"] = {"expected_sha256": h_exp.hexdigest()[:16], "database_sha256": h_act.hexdigest()[:16],
                     "records_compared": len(actual), "mismatches": mismatches, "pass": mismatches == 0}

# D. Spot check
random.seed(7)
sample = random.sample([r[0] for r in actual], 20)
with open(os.path.join(BASE, "output", "spot_check.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["source_row", "source_child_name", "db_child_name", "source_dob", "db_dob_ad", "source_phone", "db_phone",
                "source_ward", "db_ward", "checked_by", "ok?"])
    for s in sorted(sample):
        r = rows[s - 1]
        d = db.execute("SELECT child_name, dob_ad, informant_phone, ward_no FROM birth_registration WHERE source_row=?", (s,)).fetchone()
        w.writerow([s, r["child_name"], d[0], r["dob"], d[1], r["informant_phone"], d[2] or "", r["ward_no"], d[3], "", ""])
res["D_spot_check"] = "output/spot_check.csv (20 rows to check by eye)"

# E. Detection against the planted problems
rej = {r[0]: r[1] for r in q("SELECT source_row, rule_id FROM migration_reject")}
dup_rows = {r[0] for r in q("SELECT source_row FROM duplicate_review")}
warn = {}
for s, rule in q("SELECT source_row, rule_id FROM migration_warning"):
    warn.setdefault(rule, set()).add(s)
phone_null = {r[0] for r in q("SELECT source_row FROM birth_registration WHERE informant_phone IS NULL")}
sex_u = {r[0] for r in q("SELECT source_row FROM birth_registration WHERE sex='U'")}

def where(s):
    if s in rej: return f"row {s} rejected first by {rej[s]}"
    if s in dup_rows: return f"row {s} held as a duplicate first"
    return f"row {s} NOT CAUGHT"

def caught(issue, found):
    planted = set(key.get(issue, []))
    hit = planted & found
    return {"planted": len(planted), "caught": len(hit), "not_caught_by_this_rule": [where(s) for s in sorted(planted - found)]}

def caught_pairs():
    """A planted duplicate pair is caught if either copy is held for review (whichever appears
    first in the file is migrated; the other is held)."""
    pairs = {int(c): o for c, o in key["_duplicate_pairs"].items()}
    out = {"planted_pairs": len(pairs), "caught": 0, "not_caught": []}
    for copy, orig in pairs.items():
        if copy in dup_rows or orig in dup_rows:
            out["caught"] += 1
        else:
            reason = next((where(x) for x in (orig, copy) if x in rej), f"pair {orig}/{copy} NOT CAUGHT")
            out["not_caught"].append(reason)
    return out

res["E_detection"] = {
    "invalid_dob (rejected R2)": caught("invalid_dob", {s for s, r in rej.items() if r == "R2"}),
    "future_dob (rejected R2)": caught("future_dob", {s for s, r in rej.items() if r == "R2"}),
    "missing_ward (rejected R3)": caught("missing_ward", {s for s, r in rej.items() if r == "R3"}),
    "invalid_ward (rejected R3)": caught("invalid_ward", {s for s, r in rej.items() if r == "R3"}),
    "duplicate pairs (held for review R6)": caught_pairs(),
    "invalid_phone (warning R4)": caught("invalid_phone", warn.get("R4", set())),
}
planted_rejects = set(key["invalid_dob"]) | set(key["future_dob"]) | set(key["missing_ward"]) | set(key["invalid_ward"])
res["E_false_alarms"] = {"rejected_but_not_planted": len(set(rej) - planted_rejects),
                         "held_as_duplicate_but_not_planted": len(dup_rows - set(key["duplicate"])
                                                                   - {o for o in key["_duplicate_pairs"].values() if o})}
res["E_note"] = ("Each row stops at the first rule it fails, so a planted problem can be reported by an earlier "
                 "rule instead. Anything marked NOT CAUGHT is a real gap in the rules.")

res["all_pass"] = res["A_counts"]["balanced"] and res["B_each_row_once"]["pass"] and res["C_checksum"]["pass"]
json.dump(res, open(os.path.join(BASE, "output", "reconciliation.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
