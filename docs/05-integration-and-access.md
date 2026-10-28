# Integration and Access Specification

> **In simple words:** once the register is in a database, other offices (for example a central registration system) will want to check a birth record. This document says how they ask, what they're allowed to see, and who inside the ward can do what. Every change is recorded.

## 1. Lookup interface for a central system

**Purpose:** let an authorised central system confirm that a birth registration exists and matches the details it has, without exposing the whole record.

| Item | Specification |
|---|---|
| Request | `GET /v1/birth-registrations/{reg_no}` |
| Authentication | Mutual TLS plus an API key issued per calling system |
| Rate limit | 60 requests per minute per system |
| Response time | 95% of requests answered within 1 second |
| Availability | 99.5% per month, excluding announced maintenance |
| Logging | Every request logged with caller, reg_no, time and result; logs kept 2 years |

**Successful response (200):**

```json
{
  "reg_no": "BR-2079-0003",
  "child_name": "Hari Bahadur Karki",
  "sex": "M",
  "dob_ad": "2022-11-22",
  "dob_bs": "2079/08/06",
  "ward_no": 3,
  "municipality": "Kathmandu Metropolitan City",
  "status": "Registered"
}
```

Parents' names, phone and address are **not** returned; a central lookup only needs to confirm the record.

**Errors:**

| Code | When | Body |
|---|---|---|
| 400 | reg_no not in the format BR-YYYY-NNNN | `{"code":"BAD_REG_NO","message":"..."}` |
| 401 | Missing or invalid API key | — |
| 404 | No registration with that number | `{"code":"NOT_FOUND"}` |
| 409 | Record is held for duplicate review | `{"code":"UNDER_REVIEW","message":"Contact the ward office"}` |
| 429 | Rate limit exceeded | — |

## 2. Who can do what

| Role | View records | Create | Correct a record | Decide duplicates | View rejects | Export reports | Central lookup |
|---|---|---|---|---|---|---|---|
| Ward registrar | Own ward | Yes | Yes, with reason (logged) | Yes | Yes | No | — |
| Ward chairperson | Own ward | No | No | No | Yes | Yes | — |
| Municipality IT admin | All wards | No | No | No | Yes | Yes | — |
| Central system (API) | No | No | No | No | No | No | Limited fields only |

Principles: each person sees only their own ward; nobody can delete a registration; administrators manage accounts but don't edit records.

## 3. Audit requirements

| ID | Requirement |
|---|---|
| AU-01 | Every correction to a registration shall be written to `audit_log` with field, old value, new value, user, time and reason. |
| AU-02 | A correction without a reason shall be refused. |
| AU-03 | No user or application role shall be able to change or delete audit records. |
| AU-04 | Every duplicate decision (Merge or Keep) shall be logged with the user and time. |
| AU-05 | Every central lookup request shall be logged, including those refused. |
