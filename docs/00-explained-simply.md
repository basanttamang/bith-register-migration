# Birth Register Migration — Explained Simply

*A plain-language walkthrough of the project, for anyone with no technical background.* Oct 28, 2026

---

## The problem, in one sentence

A ward office's birth records sit in one messy Excel file — typed by different clerks over years — with dates in two calendars, bad ward numbers, duplicate people, and phone numbers written five different ways.

## The solution, in one sentence

**A script that automatically reads the messy file, cleans every row using fixed rules, and loads the clean version into a proper database — while keeping proof that nothing was lost.**

---

## The story, in 8 steps

### Step 1 — Invent realistic messy data (on purpose)

Since real citizens' data can't be used, a script creates 2,000 fake people and *deliberately* plants realistic mistakes as it writes them — wrong dates, bad ward numbers, duplicate entries, messy phone numbers. Because the mistakes are planted on purpose, there's an answer key for checking later whether the cleanup actually caught everything.

> Like a fire drill: the "fire" is staged on purpose so you can test whether the plan actually works.

### Step 2 — Measure the mess (before touching anything)

A script reads all 2,000 rows and simply **counts** the problems — nothing is fixed yet. This becomes the **Data Quality Report**.

| Problem found | How common |
| --- | --- |
| Dates in 2 calendars, 4 formats | Most rows |
| Inconsistent "Male/Female" spelling | 185 rows |
| Invalid ward numbers | 15 rows |
| Badly formatted phone numbers | 40 rows |
| Duplicate people | 60 rows |

> Like a home inspector's report before any repairs begin.

### Step 3 — Design where the clean data should live

Before writing any cleanup code, the new, tidy database is designed: what tables exist, what each column holds, and what format each value must be in (a real date — not free text, for example).

> Like designing clean, labeled shelving in a new house before moving any boxes in.

### Step 4 — Write one clear rule per problem

For every mess found in Step 2, one small, testable rule is written:

| Rule | What it does |
| --- | --- |
| R1 | If the year looks like Bikram Sambat, convert the date to the English calendar |
| R2 | Strip spaces/dashes from a phone number and add the +977 country code |
| R3 | Reject the row if the ward number isn't between 1 and 32 |
| R6 | If name + birth date exactly match another row, hold it for a human to check — never auto-delete |

Every decision is traceable to a named rule — nothing happens invisibly.

### Step 5 — Build the script that applies the rules

This is the actual fix. It reads every row, runs it through the rules in order, and sorts each one into exactly one of three outcomes:

| Outcome | What it means |
| --- | --- |
| ✅ Migrated cleanly | The row is clean and moved to the new database |
| ⚠️ Held for human review | Looks like a duplicate — a person decides, the script doesn't guess |
| ❌ Rejected | Too broken to fix automatically, with a stated reason |

### Step 6 — Prove the move was complete and correct

After migrating, a script checks two things:

1. **Completeness** — migrated + held + rejected = the original 2,000 rows? (Yes.)
2. **Accuracy** — did the rules catch every problem planted back in Step 1? (Yes — confirmed against the answer key.)

**Actual result from running it:**

|  | Rows |
| --- | --- |
| Migrated successfully | 1,883 |
| Held for duplicate review | 57 |
| Rejected, with a reason | 60 |
| **Total (must equal 2,000)** | **2,000 ✓** |

### Step 7 — Decide who can use the clean data afterward

Once the data is clean, other systems may need to look someone up (a bank confirming a birth certificate is real, for example). Rules are written for: who is allowed to search, what they're allowed to see (never everything), and that every lookup is logged.

> Like deciding who gets a key to the new house, and keeping a logbook of every visitor.

### Step 8 — Write it up in plain English

Every step above produces raw numbers and code. The final pass turns each one into a plain-language document with an "In simple words" box at the top — so anyone without a technical background can follow the story without reading code.

---

## Proof it actually works — real before/after examples

| Record | Before (messy) | After (clean) |
| --- | --- | --- |
| BR-2078-0001 | dob: `28-06-2078` · phone: `980 352 4248` | dob: `2021-10-14` · phone: `+9779803524248` |
| BR-2080-0002 | dob: `2080/07/30` · phone: `+977-9850869365` | dob: `2023-11-16` · phone: `+9779850869365` |
| BR-2079-0003 | dob: `2079/08/06` · phone: `+977-9881920254` | dob: `2022-11-22` · phone: `+9779881920254` |

The Bikram Sambat dates were converted automatically, and every phone number was standardized — no person touched a single row by hand.

---

## The one-breath answer for an interview

> "I wrote a set of cleaning rules and a migration script that automatically converts dates between calendars, validates ward numbers, catches duplicates, and standardizes phone numbers — then loads everything into a proper database. I proved it worked by reconciling all 2,000 original rows against the output: every row accounted for, zero mismatches."

---

## Where each step lives in the project files

| Step | File |
| --- | --- |
| 1. Invent messy data | `scripts/generate_register.py` |
| 2. Measure the mess | `scripts/profile_register.py` → `docs/01-data-quality-report.docx` |
| 3. Design clean database | `sql/schema.sql` → `docs/02-target-data-model.docx` |
| 4. Write the rules | `scripts/rules.py` → `docs/03-mapping-specification.docx` |
| 5. Apply the rules | `scripts/migrate.py` |
| 6. Prove it worked | `scripts/reconcile.py` → `docs/04-reconciliation-report.docx` |
| 7. Access rules | `docs/05-integration-and-access.docx` |
