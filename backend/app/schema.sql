-- InforSure SQLite schema (thesis sections 5, 7, 14.2).
-- Model files/checkpoints are NOT stored here; model_versions only references them.

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic               TEXT NOT NULL,
    normalized_claim    TEXT,
    evidence_text       TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    publication_date    TEXT,
    review_status       TEXT NOT NULL DEFAULT 'Pending'
                        CHECK (review_status IN ('Pending', 'Validated', 'Rejected')),
    embedding_reference TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    reviewed_by         TEXT,
    license_note        TEXT,
    review_note         TEXT,
    reviewed_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence (review_status);

-- Only validated evidence may be retrieved for verification.
CREATE VIEW IF NOT EXISTS validated_evidence AS
    SELECT * FROM evidence WHERE review_status = 'Validated';

CREATE TABLE IF NOT EXISTS dataset_versions (
    dataset_version TEXT PRIMARY KEY,
    description     TEXT,
    sample_count    INTEGER,
    artifact_path   TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS model_versions (
    model_version     TEXT PRIMARY KEY,
    dataset_version   TEXT REFERENCES dataset_versions (dataset_version),
    metrics_json      TEXT,
    artifact_path     TEXT NOT NULL,
    deployment_status TEXT NOT NULL DEFAULT 'Candidate'
                      CHECK (deployment_status IN ('Candidate', 'Deployed', 'Retired')),
    trained_at        TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
-- At most one deployed model at a time.
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_deployed_model
    ON model_versions (deployment_status) WHERE deployment_status = 'Deployed';

-- User feedback events. review_status is the queue state; the decision log is feedback_reviews.
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_text       TEXT NOT NULL,
    model_prediction TEXT NOT NULL CHECK (model_prediction IN ('Reliable', 'Misinformation')),
    model_confidence REAL CHECK (model_confidence BETWEEN 0 AND 1),
    evidence_result  TEXT CHECK (evidence_result IN ('Supported', 'Contradicted', 'Insufficient Evidence')),
    user_feedback    TEXT NOT NULL CHECK (user_feedback IN ('Agree', 'Disagree', 'Flag')),
    review_status    TEXT NOT NULL DEFAULT 'Pending'
                     CHECK (review_status IN ('Pending', 'Validated', 'Rejected')),
    model_version    TEXT REFERENCES model_versions (model_version),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback (review_status);

CREATE TABLE IF NOT EXISTS feedback_reviews (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id     INTEGER NOT NULL REFERENCES feedback (feedback_id),
    review_status   TEXT NOT NULL CHECK (review_status IN ('Validated', 'Rejected')),
    validated_label TEXT CHECK (validated_label IN ('Reliable', 'Misinformation')),
    reviewer        TEXT NOT NULL,
    notes           TEXT,
    reviewed_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- a validated review must carry the approved label
    CHECK (review_status <> 'Validated' OR validated_label IS NOT NULL)
);

-- Which validated feedback samples belong to each training release.
CREATE TABLE IF NOT EXISTS dataset_version_samples (
    dataset_version TEXT    NOT NULL REFERENCES dataset_versions (dataset_version),
    feedback_id     INTEGER NOT NULL REFERENCES feedback (feedback_id),
    PRIMARY KEY (dataset_version, feedback_id)
);

-- Re-ingesting the same source passage must not create duplicates.
CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_unique ON evidence (source_url, evidence_text);
