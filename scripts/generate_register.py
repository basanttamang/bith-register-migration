"""
Generate a fake, deliberately messy ward birth register (legacy Excel export).

All people are invented. No real citizen data is used.

Outputs:
  data/legacy_birth_register.csv   - the "old system" file to be migrated
  data/injected_issues.json        - answer key: which rows have which problems,
                                     used later to check that the migration caught them

Run:  python scripts/generate_register.py
"""
import csv, json, random, os
from datetime import date, timedelta
import nepali_datetime as nd

random.seed(2081)  # same output every run
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)

FIRST_M = ["Ram", "Hari", "Krishna", "Shyam", "Bikash", "Suman", "Anil", "Rajesh", "Prakash", "Dipak",
           "Sanjay", "Nabin", "Roshan", "Kiran", "Sujan", "Aayush", "Prabin", "Ramesh", "Gopal", "Bishal"]
FIRST_F = ["Sita", "Gita", "Anita", "Sunita", "Laxmi", "Sabina", "Puja", "Asmita", "Kamala", "Sarita",
           "Rojina", "Nisha", "Pratima", "Bimala", "Srijana", "Manisha", "Rita", "Samjhana", "Dipa", "Anju"]
MIDDLE_M = ["Bahadur", "Prasad", "Kumar", "Raj", "", "", ""]
MIDDLE_F = ["Kumari", "Devi", "Maya", "", "", ""]
SURNAMES = ["Shrestha", "Tamang", "Gurung", "Magar", "Rai", "Limbu", "Thapa", "Karki", "Adhikari", "Maharjan",
            "Basnet", "Khadka", "Lama", "Sherpa", "Bhattarai", "Poudel", "Pandey", "Shakya", "Bajracharya", "KC"]
TOLES = ["Baneshwor", "Thapathali", "Kalopul", "Battisputali", "Tinkune", "Koteshwor", "Sinamangal",
         "Gaushala", "Chabahil", "Maitidevi", "Dillibazar", "Putalisadak"]

def name(first_list, middle_list, surname):
    parts = [random.choice(first_list), random.choice(middle_list), surname]
    return " ".join(p for p in parts if p)

def random_phone():
    return random.choice(["984", "985", "986", "980", "981", "982", "974", "976", "961", "988"]) + \
        "".join(random.choice("0123456789") for _ in range(7))

# ---------- 1. Clean base records ----------
N_BASE, N_DUP = 1940, 60
records = []
for i in range(N_BASE):
    surname = random.choice(SURNAMES)
    sex = random.choice(["M", "F"])
    child = name(FIRST_M if sex == "M" else FIRST_F, MIDDLE_M if sex == "M" else MIDDLE_F, surname)
    dob_ad = date(2019, 4, 14) + timedelta(days=random.randint(0, 5 * 365))      # 2076–2081 BS
    reg_ad = dob_ad + timedelta(days=random.randint(3, 34))                        # registered within 35 days
    reg_bs = nd.date.from_datetime_date(reg_ad)
    records.append({
        "child_name": child, "sex": sex, "dob_ad": dob_ad,
        "father_name": name(FIRST_M, MIDDLE_M, surname),
        "mother_name": name(FIRST_F, MIDDLE_F, random.choice(SURNAMES)),
        "ward_no": str(random.randint(1, 32)), "tole": random.choice(TOLES),
        "phone": random_phone(), "registered_on": reg_bs.strftime("%Y/%m/%d"),
        "issues": [],
    })

# ---------- 2. Duplicates (copies entered twice, often typed differently) ----------
for _ in range(N_DUP):
    src = random.randrange(N_BASE)
    dup = dict(records[src]); dup["issues"] = ["duplicate"]; dup["duplicate_of"] = src
    style = random.choice(["exact", "abbrev", "case"])
    if style == "abbrev":
        dup["child_name"] = dup["child_name"].replace("Bahadur", "Bdr").replace("Prasad", "Pd.").replace("Kumari", "Kumari.")
    elif style == "case":
        dup["child_name"] = "  " + dup["child_name"].upper() + " "
    records.insert(random.randint(0, len(records)), dup)

# ---------- 3. Registration numbers (assigned in file order, like a real register) ----------
for n, r in enumerate(records, start=1):
    r["reg_no"] = f"BR-{r['registered_on'][:4]}-{n:04d}"

# ---------- 4. Format the date of birth the way different clerks typed it ----------
def fmt_dob(d_ad):
    bs = nd.date.from_datetime_date(d_ad)
    style = random.choices(["bs_slash", "bs_dash_dmy", "ad_iso", "ad_slash_dmy"], [45, 15, 30, 10])[0]
    return {
        "bs_slash": bs.strftime("%Y/%m/%d"),
        "bs_dash_dmy": bs.strftime("%d-%m-%Y"),
        "ad_iso": d_ad.isoformat(),
        "ad_slash_dmy": d_ad.strftime("%d/%m/%Y"),
    }[style], style

for r in records:
    r["dob_text"], r["dob_style"] = fmt_dob(r["dob_ad"])

# ---------- 5. Inject data quality problems ----------
idx = list(range(len(records)))
def pick(k, exclude_dups=True, avoid=()):
    pool = [i for i in idx if not (exclude_dups and "duplicate" in records[i]["issues"])
            and not any(a in records[i]["issues"] for a in avoid)]
    return random.sample(pool, k)

for i in pick(10):                                   # impossible or blank dates
    records[i]["dob_text"] = random.choice(["2079/13/05", "2078/02/40", "", "31-02-2020", "N/A"])
    records[i]["issues"].append("invalid_dob")
for i in pick(5, avoid=["invalid_dob"]):             # date of birth in the future
    records[i]["dob_text"] = random.choice(["2027-03-15", "2084/01/10"])
    records[i]["issues"].append("future_dob")
for i in pick(30):                                   # ward number missing
    records[i]["ward_no"] = ""
    records[i]["issues"].append("missing_ward")
for i in pick(15, avoid=["missing_ward"]):           # ward number out of range
    records[i]["ward_no"] = random.choice(["0", "33", "99", "40"])
    records[i]["issues"].append("invalid_ward")
for i in pick(120, exclude_dups=False):              # phone missing
    records[i]["phone"] = ""
    records[i]["issues"].append("missing_phone")
for i in pick(40, avoid=["missing_phone"]):          # phone not a valid mobile
    if records[i]["phone"]:
        records[i]["phone"] = random.choice(["01-4" + str(random.randint(100000, 999999)), records[i]["phone"][:8]])
        records[i]["issues"].append("invalid_phone")
for r in records:                                    # phone typed in different formats (valid but messy)
    if r["phone"] and "invalid_phone" not in r["issues"] and random.random() < 0.35:
        p = r["phone"]
        r["phone"] = random.choice([f"+977-{p}", f"977{p}", f"{p[:3]} {p[3:6]} {p[6:]}", f"+977 {p}"])
for r in records:                                    # sex recorded inconsistently
    if random.random() < 0.3:
        r["sex"] = {"M": random.choice(["Male", "male", "m"]), "F": random.choice(["Female", "female", "f"])}[r["sex"]]
for i in pick(12):
    records[i]["sex"] = ""
    records[i]["issues"].append("missing_sex")

# ---------- 6. Write files ----------
cols = ["reg_no", "child_name", "sex", "dob", "father_name", "mother_name", "ward_no", "tole", "informant_phone", "registered_on"]
with open(os.path.join(OUT, "legacy_birth_register.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in records:
        w.writerow([r["reg_no"], r["child_name"], r["sex"], r["dob_text"], r["father_name"], r["mother_name"],
                    r["ward_no"], r["tole"], r["phone"], r["registered_on"]])

key = {}
for row_no, r in enumerate(records, start=1):
    for issue in r["issues"]:
        key.setdefault(issue, []).append(row_no)
key["_note"] = "Row numbers are 1-based data rows (header excluded). Duplicates list the copy, not the original."
pairs = {}
base_by_src = {}
for n, r in enumerate(records, start=1):
    if "duplicate" not in r["issues"]:
        base_by_src.setdefault((r["father_name"], r["mother_name"], r["dob_ad"]), n)
for n, r in enumerate(records, start=1):
    if "duplicate" in r["issues"]:
        pairs[str(n)] = base_by_src.get((r["father_name"], r["mother_name"], r["dob_ad"]))
key["_duplicate_pairs"] = pairs
with open(os.path.join(OUT, "injected_issues.json"), "w") as f:
    json.dump(key, f, indent=1)

print(f"Wrote {len(records)} rows to data/legacy_birth_register.csv")
print({k: len(v) for k, v in key.items() if not k.startswith('_')})
