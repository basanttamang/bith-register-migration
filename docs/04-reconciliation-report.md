# Reconciliation Report

**Migration run:** `scripts/migrate.py` · **Checked with:** `scripts/reconcile.py` · **Result: all checks passed**

> **In simple words:** after moving the data, I proved nothing was lost or changed by mistake. Every one of the 2,000 old rows ended up in exactly one place, and every migrated record matches what the rules say it should be.

## Where every row went

| Destination | Rows | % | What happens next |
|---|---|---|---|
| Migrated to `birth_registration` | 1,883 | 94.2% | Live in the new system |
| Held in `duplicate_review` | 57 | 2.9% | Ward registrar confirms Merge or Keep |
| Rejected to `migration_reject` | 60 | 3.0% | Ward officer corrects and re-loads |
| **Total** | **2,000** | **100%** | Matches the source file |

Rejected rows by reason: 45 ward missing or out of range (R3), 15 date of birth impossible, blank or in the future (R2).

Migrated records with warnings: 38 invalid phone numbers stored as blank (R4), 12 with sex not recorded (R5).

## Checks

| Check | What it proves | Result |
|---|---|---|
| A. Counts balance | 1,883 + 57 + 60 = 2,000 source rows | Pass |
| B. Each row exactly once | No row missing, none counted twice | Pass: 2,000 accounted, 0 missing, 0 twice |
| C. Content checksum | Every migrated record was re-derived from the source using the same rules and compared field by field | Pass: 1,883 compared, 0 mismatches, checksums match (`e541db73b6dfbe04`) |
| D. Spot check by eye | A person compares 20 random records with the old file | See `output/spot_check.csv` — [to be signed off] |
| E. Problems detected | Every problem planted in the test data was caught | Pass, with 0 false alarms (below) |

## Did the rules catch every planted problem?

The test data was generated with a list of exactly which rows had which problems. This compares the migration against that list.

| Planted problem | Planted | Caught by intended rule | Caught by an earlier rule | Not caught |
|---|---|---|---|---|
| Impossible, blank or unreadable date | 10 | 10 | 0 | 0 |
| Future date of birth | 5 | 5 | 0 | 0 |
| Missing ward | 30 | 30 | 0 | 0 |
| Ward out of range | 15 | 15 | 0 | 0 |
| Duplicate pair | 60 | 57 | 3 (original rejected for missing ward) | 0 |
| Invalid phone | 40 | 38 | 2 (row rejected for ward or date) | 0 |

**False alarms:** 0 rows rejected and 0 rows held as duplicates that didn't have a planted problem.

## Finding: duplicates hidden behind rejected rows

In 3 duplicate pairs, the first copy had a missing ward and was rejected, so the second copy was migrated as if it were unique. When the ward officer fixes and re-loads the rejected row, it **must go through the duplicate check (R6) again**, or the same child will be registered twice.

**Recommendation:** re-loading corrected rejects uses the same migration script, never a direct insert.

## Sign-off

| Name | Role | Spot check done | Date |
|---|---|---|---|
| | Ward registrar (or tester) | | |
