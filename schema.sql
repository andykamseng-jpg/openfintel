CREATE TABLE IF NOT EXISTS uploads (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('general_ledger', 'income_statement', 'cash_flow', 'balance_sheet')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS income_statement (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    period DATE,
    line_item TEXT NOT NULL,
    category TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cash_flow (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    period DATE,
    line_item TEXT NOT NULL,
    cash_flow_type TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS balance_sheet (
    id BIGSERIAL PRIMARY KEY,
    upload_id BIGINT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    as_of_date DATE,
    line_item TEXT NOT NULL,
    section TEXT,
    amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS upload_logs (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT,
    doc_type TEXT,
    rows_uploaded INTEGER NOT NULL DEFAULT 0,
    rows_inserted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
