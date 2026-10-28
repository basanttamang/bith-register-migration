"""
Migrate the legacy birth register into the new database.

Three stages, as in docs/03-mapping-specification.md:
  1. Load   - copy every row of the CSV into a staging table, unchanged
  2. Clean  - apply rules R1–R6 to each row
  3. Insert - good rows go to birth_registration; failed rows go to
              migration_reject with a reason; likely second entries go to
              duplicate_review. Nothing is silently dropped.

Uses SQLite (built into Python) so it runs on any laptop. The production
design for PostgreSQL is in sql/schema.sql.

Run:  python scripts/migrate.py
"""
import csv, json, os, sqlite3
from datetime import date
import rules

BASE = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(BASE, "data", "legacy_birth_register.csv")
OUT = os.path.join(BASE, "output"); os.makedirs(OUT, exist_ok=True)
DB = os.path.join(OUT, "register.db")
TODAY = date.today()

if os.path.exists(DB):
    os.remove(DB)
db = sqlite3.connect(DB)
db.executescript("""
PRAGMA foreign_keys = ON;
CREATE TABLE staging_register (source_row INTEGER PRIMARY KEY, reg_no TEXT, child_name TEXT, sex TEXT, dob TEXT,
  father_name TEXT, mother_name TEXT, ward_no TEXT, tole TEXT, informant_phone TEXT, registered_on TEXT);
CREATE TABLE ward (ward_no INTEGER PRIMARY KEY CHECK (ward_no BETWEEN 1 AND 32), municipality TEXT NOT NULL);
CREATE TABLE birth_registration (
  registration_id INTEGER PRIMARY KEY AUTOINCREMENT, reg_no TEXT NOT NULL UNIQUE, child_name TEXT NOT NULL,
  sex TEXT NOT NULL CHECK (sex IN ('M','F','O','U')), dob_ad TEXT NOT NULL, dob_original TEXT NOT NULL,
  dob_calendar TEXT NOT NULL CHECK (dob_calendar IN ('BS','AD')), father_name TEXT NOT NULL, mother_name TEXT NOT NULL,
  ward_no INTEGER NOT NULL REFERENCES ward(ward_no), tole TEXT, informant_phone TEXT, registered_on_bs TEXT NOT NULL,
  source_row INTEGER NOT NULL UNIQUE, migrated_at TEXT NOT NULL);
CREATE TABLE migration_reject (source_row INTEGER PRIMARY KEY, reg_no TEXT, rule_id TEXT NOT NULL, reason TEXT NOT NULL, raw_record TEXT NOT NULL);
CREATE TABLE duplicate_review (source_row INTEGER PRIMARY KEY, reg_no TEXT NOT NULL,
  matches_registration INTEGER NOT NULL REFERENCES birth_registration(registration_id), match_rule TEXT NOT NULL,
  decision TEXT NOT NULL DEFAULT 'Pending');
CREATE TABLE migration_warning (source_row INTEGER NOT NULL, rule_id TEXT NOT NULL, detail TEXT NOT NULL);
""")
db.executemany("INSERT INTO ward VALUES (?, 'Kathmandu Metropolitan City')", [(w,) for w in range(1, 33)])

# ---------- Stage 1: load unchanged ----------
with open(SRC, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
cols = list(rows[0].keys())
db.executemany(f"INSERT INTO staging_register VALUES (?{',?' * len(cols)})",
               [(i, *[r[c] for c in cols]) for i, r in enumerate(rows, start=1)])

# ---------- Stages 2 and 3: clean, then insert or set aside ----------
seen = {}          # duplicate match key -> registration_id
now = TODAY.isoformat()
counts = {"migrated": 0, "rejected": 0, "duplicate_review": 0, "warnings": 0}

def reject(i, r, rule_id, reason):
    db.execute("INSERT INTO migration_reject VALUES (?,?,?,?,?)",
               (i, r["reg_no"], rule_id, reason, json.dumps(r, ensure_ascii=False)))
    counts["rejected"] += 1

def warn(i, rule_id, detail):
    db.execute("INSERT INTO migration_warning VALUES (?,?,?)", (i, rule_id, detail))
    counts["warnings"] += 1

for i, r in enumerate(rows, start=1):
    dob_ad, cal, err = rules.parse_date(r["dob"], TODAY)                       # R2
    if err:
        reject(i, r, "R2", err); continue
    ward, err = rules.parse_ward(r["ward_no"])                                # R3
    if err:
        reject(i, r, "R3", err); continue

    child, father, mother = (rules.clean_name(r[k]) for k in ("child_name", "father_name", "mother_name"))  # R1
    phone, phone_status = rules.parse_phone(r["informant_phone"])             # R4
    if phone_status == "invalid":
        warn(i, "R4", f"Phone '{r['informant_phone']}' is not a valid mobile number; stored as blank")
    sex, sex_status = rules.parse_sex(r["sex"])                               # R5
    if sex_status in ("missing", "unrecognised"):
        warn(i, "R5", f"Sex '{r['sex']}' not recorded; stored as U")

    key = (rules.match_key(child), dob_ad, rules.match_key(mother))           # R6
    if key in seen:
        db.execute("INSERT INTO duplicate_review (source_row, reg_no, matches_registration, match_rule) VALUES (?,?,?,?)",
                   (i, r["reg_no"], seen[key], "Same child name, date of birth and mother's name"))
        counts["duplicate_review"] += 1
        continue

    cur = db.execute("""INSERT INTO birth_registration (reg_no, child_name, sex, dob_ad, dob_original, dob_calendar,
        father_name, mother_name, ward_no, tole, informant_phone, registered_on_bs, source_row, migrated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (r["reg_no"], child, sex, dob_ad.isoformat(), r["dob"].strip(), cal, father, mother, ward,
         r["tole"].strip() or None, phone, r["registered_on"].strip(), i, now))
    seen[key] = cur.lastrowid
    counts["migrated"] += 1

db.commit()
counts["source_rows"] = len(rows)
json.dump(counts, open(os.path.join(OUT, "migration_summary.json"), "w"), indent=1)
print(json.dumps(counts, indent=1))
print("Database written to output/register.db")
