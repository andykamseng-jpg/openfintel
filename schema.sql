CREATE TABLE IF NOT EXISTS uploads (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('general_ledger', 'income_statement', 'cash_flow', 'balance_sheet')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE uploads ADD COLUMN IF NOT EXISTS filename TEXT NOT NULL DEFAULT 'unknown.csv';
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'income_statement';
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS general_ledger (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    transaction_date DATE,
    description TEXT,
    account TEXT,
    category TEXT,
    debit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    credit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    fingerprint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS upload_id BIGINT REFERENCES uploads(id) ON DELETE CASCADE;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS transaction_date DATE;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS account TEXT;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS debit NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS credit NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS amount NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS fingerprint TEXT;
ALTER TABLE general_ledger ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS income_statement (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    period DATE,
    line_item TEXT NOT NULL,
    category TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE income_statement ADD COLUMN IF NOT EXISTS upload_id BIGINT REFERENCES uploads(id) ON DELETE CASCADE;
ALTER TABLE income_statement ADD COLUMN IF NOT EXISTS period DATE;
ALTER TABLE income_statement ADD COLUMN IF NOT EXISTS line_item TEXT NOT NULL DEFAULT '';
ALTER TABLE income_statement ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE income_statement ADD COLUMN IF NOT EXISTS amount NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE income_statement ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS cash_flow (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    period DATE,
    line_item TEXT NOT NULL,
    cash_flow_type TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE cash_flow ADD COLUMN IF NOT EXISTS upload_id BIGINT REFERENCES uploads(id) ON DELETE CASCADE;
ALTER TABLE cash_flow ADD COLUMN IF NOT EXISTS period DATE;
ALTER TABLE cash_flow ADD COLUMN IF NOT EXISTS line_item TEXT NOT NULL DEFAULT '';
ALTER TABLE cash_flow ADD COLUMN IF NOT EXISTS cash_flow_type TEXT;
ALTER TABLE cash_flow ADD COLUMN IF NOT EXISTS amount NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE cash_flow ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS balance_sheet (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    as_of_date DATE,
    line_item TEXT NOT NULL,
    section TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE balance_sheet ADD COLUMN IF NOT EXISTS upload_id BIGINT REFERENCES uploads(id) ON DELETE CASCADE;
ALTER TABLE balance_sheet ADD COLUMN IF NOT EXISTS as_of_date DATE;
ALTER TABLE balance_sheet ADD COLUMN IF NOT EXISTS line_item TEXT NOT NULL DEFAULT '';
ALTER TABLE balance_sheet ADD COLUMN IF NOT EXISTS section TEXT;
ALTER TABLE balance_sheet ADD COLUMN IF NOT EXISTS amount NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE balance_sheet ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_uploads_type_created_at ON uploads (type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_general_ledger_upload_id ON general_ledger (upload_id);
CREATE INDEX IF NOT EXISTS idx_general_ledger_transaction_date ON general_ledger (transaction_date);
CREATE INDEX IF NOT EXISTS idx_income_statement_period ON income_statement (period);
CREATE INDEX IF NOT EXISTS idx_cash_flow_period ON cash_flow (period);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_as_of_date ON balance_sheet (as_of_date);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_section ON balance_sheet (section);

CREATE TABLE IF NOT EXISTS financial_data (
    id BIGSERIAL PRIMARY KEY,
    date DATE,
    description TEXT,
    category TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    doc_type TEXT,
    fingerprint TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS date DATE;
ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS amount NUMERIC(14, 2) NOT NULL DEFAULT 0;
ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS doc_type TEXT;
ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS fingerprint TEXT;
ALTER TABLE financial_data ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS upload_logs (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT,
    doc_type TEXT,
    rows_uploaded INTEGER NOT NULL DEFAULT 0,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE upload_logs ADD COLUMN IF NOT EXISTS filename TEXT;
ALTER TABLE upload_logs ADD COLUMN IF NOT EXISTS doc_type TEXT;
ALTER TABLE upload_logs ADD COLUMN IF NOT EXISTS rows_uploaded INTEGER NOT NULL DEFAULT 0;
ALTER TABLE upload_logs ADD COLUMN IF NOT EXISTS rows_inserted INTEGER NOT NULL DEFAULT 0;
ALTER TABLE upload_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
