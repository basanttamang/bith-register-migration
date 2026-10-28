"""
Profile the legacy register: measure every data quality problem before migrating.
Results feed docs/01-data-quality-report.md.

Run:  python scripts/profile_register.py
"""
import csv, os, json
from collections import Counter, defaultdict
import rules

SRC = os.path.join(os.path.dirname(__file__), "..", "data", "legacy_birth_register.csv")
rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
n = len(rows)
out = {"rows": n, "columns": list(rows[0].keys())}

out["blank_values"] = {c: sum(1 for r in rows if not r[c].strip()) for c in rows[0]}

fmt = Counter()
for r in rows:
    name, cal = rules.classify_date(r["dob"])
    fmt[f"{name} ({cal})" if cal else name] += 1
out["dob_formats"] = dict(fmt.most_common())
out["dob_problems"] = Counter(("future" if "future" in e else "not a real date" if "not a real" in e
                               else "blank" if "blank" in e else "unrecognised format")
                              for r in rows for _, _, e in [rules.parse_date(r["dob"])] if e)

out["ward"] = Counter(("missing" if not r["ward_no"].strip() else
                       "valid" if rules.parse_ward(r["ward_no"])[1] is None else "out of range") for r in rows)
out["phone"] = Counter(rules.parse_phone(r["informant_phone"])[1] for r in rows)
out["sex_values"] = Counter(r["sex"] or "(blank)" for r in rows)
out["reg_no_unique"] = len({r["reg_no"] for r in rows}) == n

groups = defaultdict(list)
for i, r in enumerate(rows, start=1):
    ad, _, err = rules.parse_date(r["dob"])
    if err:
        continue
    groups[(rules.match_key(r["child_name"]), ad, rules.match_key(r["mother_name"]))].append(i)
dups = [g for g in groups.values() if len(g) > 1]
out["likely_duplicate_groups"] = len(dups)
out["likely_duplicate_extra_rows"] = sum(len(g) - 1 for g in dups)
out["duplicate_examples"] = [[rows[i - 1]["reg_no"] + " | " + rows[i - 1]["child_name"] for i in g] for g in dups[:3]]

names_needing_tidy = sum(1 for r in rows if rules.clean_name(r["child_name"]) != r["child_name"])
out["child_names_needing_tidy"] = names_needing_tidy

print(json.dumps(out, indent=1, default=str, ensure_ascii=False))
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "output"), exist_ok=True)
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "output", "profile.json"), "w"), indent=1, default=str)
