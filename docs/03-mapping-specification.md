# Mapping Specification

> **In simple words:** this is the instruction sheet for moving the data. For every column in the old file, it says where it goes in the new database, how it's cleaned, and what happens if it's bad.

The rules are written in code once, in [scripts/rules.py](../scripts/rules.py), and used by the profiling, migration and reconciliation scripts, so all three apply exactly the same logic.

## Process

1. **Load:** copy every row of the old file, unchanged, into a staging table with its row number.
2. **Clean and check:** apply rules R1–R6 to each row, in order. A row stops at the first rule that rejects it.
3. **Insert or set aside:** good rows go into `birth_registration`; rejected rows into `migration_reject`; likely second entries into `duplicate_review`. Warnings go into `migration_warning`.

## Column mapping

| Source column | Target column | Transformation | Validation | If it fails |
|---|---|---|---|---|
| reg_no | birth_registration.reg_no | Trim | Unique, not blank | — (all valid) |
| child_name | child_name | R1: trim, single spaces, Title Case, expand Bdr → Bahadur, Pd. → Prasad | Not blank | — |
| sex | sex | R5: M/Male/male/m → M; F/Female/female/f → F | One of M, F | Store U, log warning |
| dob | dob_ad | R2: detect format and calendar; convert BS to AD | Real date, not in the future | Reject |
| dob | dob_original | Copy as typed | — | — |
| dob | dob_calendar | BS if year ≥ 2050, else AD | — | — |
| father_name | father_name | R1 | Not blank | — |
| mother_name | mother_name | R1 | Not blank | — |
| ward_no | ward_no | R3: convert to number | Whole number 1–32 | Reject |
| tole | tole | Trim | — | Store blank |
| informant_phone | informant_phone | R4: remove spaces, dashes and 977 prefix; store as +977XXXXXXXXXX | 10 digits starting 96, 97 or 98 | Store blank, log warning |
| registered_on | registered_on_bs | Copy (always BS YYYY/MM/DD) | — | — |
| (row number) | source_row | Row number in old file | — | — |

## Rules

| ID | Rule | Example in → out |
|---|---|---|
| R1 | Tidy names | `"  RAM BDR KARKI "` → `Ram Bahadur Karki` |
| R2 | Date of birth: detect format and calendar, convert to AD, reject impossible or future dates | `2081/05/12` (BS) → `2024-08-28` · `28/08/2024` (AD) → `2024-08-28` · `2078/02/40` → reject |
| R3 | Ward must be 1–32 | `"7"` → 7 · `""` → reject · `"99"` → reject |
| R4 | Phone to standard format | `984 123 4567` → `+9779841234567` · `01-4412345` → blank + warning |
| R5 | Sex to M / F / U | `female` → F · `""` → U + warning |
| R6 | Duplicate check: same tidied child name, AD date of birth and mother's name | Second entry held in `duplicate_review` for a person to decide |

## Run order

```
pip install -r requirements.txt
python scripts/generate_register.py   # only to create the test data
python scripts/profile_register.py
python scripts/migrate.py
python scripts/reconcile.py
```
