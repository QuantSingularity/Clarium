-- Clarium RegTech Compliance Module - Database Schema

-- ── KYC ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kyc_submissions (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(256)  NOT NULL UNIQUE,
    status          VARCHAR(32)   NOT NULL DEFAULT 'pending',
    -- status: pending | processing | verified | rejected | review
    full_name       VARCHAR(512),
    date_of_birth   DATE,
    nationality     VARCHAR(8),     -- ISO 3166-1 alpha-2
    document_type   VARCHAR(64),    -- passport | national_id | driving_license
    document_number VARCHAR(256),
    document_uri    TEXT,           -- path to uploaded file
    ocr_raw         JSONB,          -- raw OCR output
    ocr_confidence  FLOAT,
    identity_score  FLOAT,          -- computed composite score 0-1
    reviewer_notes  TEXT,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at     TIMESTAMPTZ,
    rejected_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_kyc_status  ON kyc_submissions(status);
CREATE INDEX IF NOT EXISTS idx_kyc_user    ON kyc_submissions(user_id);

-- ── AML ──────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS aml_checks (
    id                  BIGSERIAL PRIMARY KEY,
    transaction_id      VARCHAR(256) NOT NULL,
    user_id             VARCHAR(256),
    amount              NUMERIC(18,4) NOT NULL,
    currency            VARCHAR(8)   NOT NULL DEFAULT 'USD',
    source_country      VARCHAR(8),
    destination_country VARCHAR(8),
    risk_score          FLOAT        NOT NULL DEFAULT 0,
    flagged             BOOLEAN      NOT NULL DEFAULT FALSE,
    flag_reasons        JSONB        DEFAULT '[]',
    pep_match           BOOLEAN      NOT NULL DEFAULT FALSE,
    pep_match_details   JSONB,
    status              VARCHAR(32)  NOT NULL DEFAULT 'clear',
    -- status: clear | flagged | under_review | escalated | cleared
    checked_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ,
    reviewer_id         VARCHAR(256)
);

CREATE INDEX IF NOT EXISTS idx_aml_transaction ON aml_checks(transaction_id);
CREATE INDEX IF NOT EXISTS idx_aml_user        ON aml_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_aml_flagged     ON aml_checks(flagged, checked_at DESC);

-- ── Audit Trail (immutable, hash-chained) ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_events (
    id              BIGSERIAL PRIMARY KEY,
    entity_type     VARCHAR(64)  NOT NULL,   -- kyc | aml | webhook | admin
    entity_id       VARCHAR(256) NOT NULL,
    event_type      VARCHAR(128) NOT NULL,   -- e.g. kyc.submitted, aml.flagged
    actor_id        VARCHAR(256),            -- user or service that caused event
    payload         JSONB        NOT NULL DEFAULT '{}',
    ip_address      INET,
    prev_hash       VARCHAR(64),             -- SHA-256 of previous row (chain)
    this_hash       VARCHAR(64) NOT NULL,    -- SHA-256 of this row content
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_entity   ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created  ON audit_events(created_at DESC);

-- ── Webhook Registrations ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS webhook_registrations (
    id              SERIAL PRIMARY KEY,
    url             TEXT         NOT NULL,
    secret          VARCHAR(256),            -- HMAC secret for signature
    events          JSONB        NOT NULL DEFAULT '["*"]',
    -- e.g. ["kyc.verified","kyc.rejected"] or ["*"] for all
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id              BIGSERIAL PRIMARY KEY,
    webhook_id      INT          NOT NULL REFERENCES webhook_registrations(id) ON DELETE CASCADE,
    event_type      VARCHAR(128) NOT NULL,
    payload         JSONB        NOT NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'pending',
    -- pending | delivered | failed | retrying
    attempts        INT          NOT NULL DEFAULT 0,
    response_code   INT,
    response_body   TEXT,
    next_retry_at   TIMESTAMPTZ,
    delivered_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_delivery_status ON webhook_deliveries(status, next_retry_at);

-- ── PEP List (Politically Exposed Persons) ────────────────────────────────────

CREATE TABLE IF NOT EXISTS pep_list (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(512) NOT NULL,
    aliases         JSONB        DEFAULT '[]',
    country         VARCHAR(8),
    position        TEXT,
    risk_level      VARCHAR(16)  NOT NULL DEFAULT 'high',
    source          VARCHAR(128),
    added_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pep_name ON pep_list USING gin(to_tsvector('english', full_name));

-- ── Seed PEP list with sample entries ────────────────────────────────────────
INSERT INTO pep_list (full_name, aliases, country, position, risk_level, source) VALUES
  ('John Doe',    '["J. Doe", "Johnny Doe"]',         'US', 'Former Minister of Finance',     'high',   'UN Sanctions List'),
  ('Jane Smith',  '["J. Smith"]',                     'UK', 'Current Deputy Governor',        'medium', 'HM Treasury'),
  ('Carlos Ruiz', '["C. Ruiz", "Carlos R."]',         'MX', 'Former State Governor',          'high',   'OFAC SDN List'),
  ('Li Wei',      '["Wei Li", "L. Wei"]',             'CN', 'Senior Party Official',          'high',   'EU Sanctions'),
  ('Ahmed Hassan','["A. Hassan", "Ahmed H."]',        'EG', 'Former Central Bank Director',   'medium', 'FATF List')
ON CONFLICT DO NOTHING;
