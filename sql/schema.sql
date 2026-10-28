-- Target data model for the ward birth register (PostgreSQL).
-- The migration script runs the same design on SQLite so it works on any laptop;
-- see scripts/migrate.py for the SQLite version of these tables.

CREATE TABLE ward (
    ward_no        SMALLINT PRIMARY KEY CHECK (ward_no BETWEEN 1 AND 32),
    municipality   VARCHAR(100) NOT NULL DEFAULT 'Kathmandu Metropolitan City'
);

CREATE TABLE birth_registration (
    registration_id   SERIAL PRIMARY KEY,
    reg_no            VARCHAR(20)  NOT NULL UNIQUE,
    child_name        VARCHAR(150) NOT NULL,
    sex               CHAR(1)      NOT NULL CHECK (sex IN ('M', 'F', 'O', 'U')),   -- U = not recorded
    dob_ad            DATE         NOT NULL CHECK (dob_ad <= CURRENT_DATE),
    dob_original      VARCHAR(20)  NOT NULL,                                       -- exactly as typed in the old register
    dob_calendar      CHAR(2)      NOT NULL CHECK (dob_calendar IN ('BS', 'AD')),  -- calendar of the original entry
    father_name       VARCHAR(150) NOT NULL,
    mother_name       VARCHAR(150) NOT NULL,
    ward_no           SMALLINT     NOT NULL REFERENCES ward (ward_no),
    tole              VARCHAR(100),
    informant_phone   VARCHAR(14)  CHECK (informant_phone ~ '^\+9779[678][0-9]{8}$'),
    registered_on_bs  VARCHAR(10)  NOT NULL,
    source_row        INTEGER      NOT NULL UNIQUE,                                -- row number in the legacy file
    migrated_at       TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX ix_birth_child_dob ON birth_registration (child_name, dob_ad);

-- Rows that failed a validation rule. Kept, not discarded, so a ward officer can fix them.
CREATE TABLE migration_reject (
    source_row  INTEGER PRIMARY KEY,
    reg_no      VARCHAR(20),
    rule_id     VARCHAR(5)  NOT NULL,
    reason      TEXT        NOT NULL,
    raw_record  JSONB       NOT NULL
);

-- Rows migrated with a value set to blank or U (e.g. invalid phone). Kept for follow-up.
CREATE TABLE migration_warning (
    source_row  INTEGER     NOT NULL,
    rule_id     VARCHAR(5)  NOT NULL,
    detail      TEXT        NOT NULL
);

-- Rows that look like a second entry of a record already migrated.
CREATE TABLE duplicate_review (
    source_row             INTEGER PRIMARY KEY,
    reg_no                 VARCHAR(20) NOT NULL,
    matches_registration   INTEGER     NOT NULL REFERENCES birth_registration (registration_id),
    match_rule             TEXT        NOT NULL,
    decision               VARCHAR(10) NOT NULL DEFAULT 'Pending' CHECK (decision IN ('Pending', 'Merged', 'Kept'))
);

-- Every later correction is recorded here. No role may UPDATE or DELETE rows in this table.
CREATE TABLE audit_log (
    audit_id         BIGSERIAL PRIMARY KEY,
    registration_id  INTEGER   NOT NULL REFERENCES birth_registration (registration_id),
    field_name       VARCHAR(50) NOT NULL,
    old_value        TEXT,
    new_value        TEXT,
    changed_by       VARCHAR(50) NOT NULL,
    changed_at       TIMESTAMP NOT NULL DEFAULT now(),
    reason           TEXT      NOT NULL
);

-- Roles (see docs/05-integration-and-access.md)
CREATE ROLE ward_registrar;
CREATE ROLE ward_chairperson;
CREATE ROLE central_lookup;

GRANT SELECT, INSERT, UPDATE ON birth_registration TO ward_registrar;
GRANT SELECT, INSERT ON audit_log TO ward_registrar;
GRANT SELECT, UPDATE (decision) ON duplicate_review TO ward_registrar;
GRANT SELECT ON birth_registration, migration_reject, duplicate_review TO ward_chairperson;
GRANT SELECT (reg_no, child_name, sex, dob_ad, ward_no) ON birth_registration TO central_lookup;
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
