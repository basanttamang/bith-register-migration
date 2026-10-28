# Data Quality Report: Legacy Birth Register

**Source:** `data/legacy_birth_register.csv` (Excel export, 2,000 rows, 10 columns)
**Profiled with:** `scripts/profile_register.py` · **Author:** Basant Tamang

> **In simple words:** before moving the old register into a new database, I counted every problem in it. This report says what's wrong, how many rows are affected, and what rule will handle each problem.

## Summary

The register is usable, but **275 rows (14%) have a real problem** (missing, invalid or duplicated data), and **1,180 rows (59%) need fixing or tidying** such as phone, sex or name formatting, on top of date conversion for every row. The most serious issues:

1. **Dates of birth are in four different formats and two calendars.** 60% are Bikram Sambat (BS), 40% Gregorian (AD), with no column saying which.
2. **45 rows (2.3%) have a missing or impossible ward number**, so they can't be assigned to a ward.
3. **60 records appear twice**, often with the name typed differently ("Ram Bahadur" / "Ram Bdr").
4. **Phone numbers are typed five different ways**, and 160 rows (8%) have no usable number.

## Findings

| # | Issue | Column | Rows affected | % | Severity | Proposed rule |
|---|---|---|---|---|---|---|
| 1 | Mixed date formats and calendars | dob | 1,996 | 99.8% | High | R2: detect format and calendar; convert BS to AD; keep the original text |
| 2 | Date of birth not a real date, blank or unreadable | dob | 10 | 0.5% | High | R2: reject for manual correction |
| 3 | Date of birth in the future | dob | 5 | 0.3% | High | R2: reject for manual correction |
| 4 | Ward number missing | ward_no | 30 | 1.5% | High | R3: reject; ward officer assigns ward |
| 5 | Ward number outside 1–32 (0, 33, 40, 99) | ward_no | 15 | 0.8% | High | R3: reject; ward officer corrects |
| 6 | Likely duplicate records | all | 60 | 3.0% | Medium | R6: migrate the first, hold the second for review |
| 7 | Phone in non-standard format (+977-, 977, spaces) | informant_phone | 630 | 31.5% | Low | R4: strip to 10 digits, store as +977XXXXXXXXXX |
| 8 | Phone missing | informant_phone | 120 | 6.0% | Low | R4: store as blank |
| 9 | Phone not a valid mobile (landline, too short) | informant_phone | 40 | 2.0% | Low | R4: store as blank, log a warning |
| 10 | Sex recorded six different ways (M, Male, male, m…) | sex | 589 | 29.5% | Low | R5: standardise to M / F |
| 11 | Sex blank | sex | 12 | 0.6% | Low | R5: store as U (not recorded), log a warning |
| 12 | Names with extra spaces, capitals or abbreviations | child_name | 25 | 1.3% | Low | R1: tidy spacing and case; expand Bdr, Pd. |

`reg_no` is unique in every row, so it can be kept as the registration number.

## Date of birth formats found

| Format as typed | Calendar | Rows | Example |
|---|---|---|---|
| YYYY/MM/DD | BS | 908 | 2079/08/06 |
| YYYY-MM-DD | AD | 593 | 2023-08-19 |
| DD-MM-YYYY | BS | 284 | 28-06-2078 |
| DD/MM/YYYY | AD | 211 | 26/11/2023 |
| Blank | — | 3 | |
| Unreadable | — | 1 | N/A |

**How the calendar is detected:** any year of 2050 or above is treated as BS (2050 BS is 1993 AD). This is safe for this register because every AD birth year in it is between 2019 and 2027. It must be reviewed before reusing the rule on older records.

## Questions for the ward office

These need a business decision, not a technical one:

1. When a ward number is missing, can it be taken from the address (tole), or must a person decide?
2. When two records are duplicates, which registration number is the official one?
3. Should records with an invalid phone number be followed up, or is the phone optional?
4. Is "U" (not recorded) acceptable for sex in the official register?
