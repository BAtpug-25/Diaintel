-- DiaIntel Database Schema
-- PostgreSQL + TimescaleDB

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- Table: raw_posts
-- Stores raw Reddit posts loaded from Pushshift .zst dump files
-- ============================================================
CREATE TABLE IF NOT EXISTS raw_posts (
    id              SERIAL PRIMARY KEY,
    reddit_id       VARCHAR(20) UNIQUE NOT NULL,
    subreddit       VARCHAR(100) NOT NULL,
    body            TEXT NOT NULL,
    score           INTEGER DEFAULT 0,
    comment_count   INTEGER DEFAULT 0,
    created_utc     TIMESTAMPTZ NOT NULL,
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    processed       BOOLEAN DEFAULT FALSE,
    source_file     VARCHAR(255)
);

CREATE INDEX idx_raw_posts_subreddit ON raw_posts(subreddit);
CREATE INDEX idx_raw_posts_processed ON raw_posts(processed);
CREATE INDEX idx_raw_posts_source_file ON raw_posts(source_file);
CREATE INDEX idx_raw_posts_created_utc ON raw_posts(created_utc);

-- ============================================================
-- Table: processed_posts
-- Stores cleaned and processed versions of raw posts
-- ============================================================
CREATE TABLE IF NOT EXISTS processed_posts (
    id              SERIAL PRIMARY KEY,
    raw_post_id     INTEGER NOT NULL REFERENCES raw_posts(id) ON DELETE CASCADE,
    cleaned_text    TEXT NOT NULL,
    language        VARCHAR(10) DEFAULT 'en',
    word_count      INTEGER DEFAULT 0,
    processed_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_processed_posts_raw_post_id ON processed_posts(raw_post_id);

-- ============================================================
-- Table: drug_mentions
-- Stores detected drug name mentions with dosage info
-- ============================================================
CREATE TABLE IF NOT EXISTS drug_mentions (
    id              SERIAL PRIMARY KEY,
    post_id         INTEGER NOT NULL REFERENCES processed_posts(id) ON DELETE CASCADE,
    drug_name       VARCHAR(100) NOT NULL,
    drug_normalized VARCHAR(100) NOT NULL,
    dosage          VARCHAR(50),
    frequency       VARCHAR(100),
    confidence      FLOAT DEFAULT 0.0,
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drug_mentions_drug_normalized ON drug_mentions(drug_normalized);
CREATE INDEX idx_drug_mentions_post_id ON drug_mentions(post_id);

-- ============================================================
-- Table: ae_signals
-- Stores detected adverse event signals
-- ============================================================
CREATE TABLE IF NOT EXISTS ae_signals (
    id              SERIAL PRIMARY KEY,
    post_id         INTEGER NOT NULL REFERENCES processed_posts(id) ON DELETE CASCADE,
    drug_name       VARCHAR(100) NOT NULL,
    ae_term         VARCHAR(200) NOT NULL,
    ae_normalized   VARCHAR(200),
    severity        VARCHAR(20) DEFAULT 'unknown',
    confidence      FLOAT DEFAULT 0.0,
    temporal_marker VARCHAR(200),
    detected_at     TIMESTAMPTZ DEFAULT NOW(),
    is_new_signal   BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_ae_signals_drug_name ON ae_signals(drug_name);
CREATE INDEX idx_ae_signals_detected_at ON ae_signals(detected_at);
CREATE INDEX idx_ae_signals_post_id ON ae_signals(post_id);
CREATE INDEX idx_ae_signals_ae_term ON ae_signals(ae_term);

-- ============================================================
-- Table: sentiment_scores
-- Stores per-drug sentiment analysis results
-- ============================================================
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id              SERIAL PRIMARY KEY,
    post_id         INTEGER NOT NULL REFERENCES processed_posts(id) ON DELETE CASCADE,
    drug_name       VARCHAR(100) NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    sentiment_score FLOAT DEFAULT 0.0,
    confidence      FLOAT DEFAULT 0.0,
    scored_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sentiment_scores_drug_name ON sentiment_scores(drug_name);
CREATE INDEX idx_sentiment_scores_post_id ON sentiment_scores(post_id);

-- ============================================================
-- Table: misinfo_flags
-- Stores flagged potential misinformation posts
-- ============================================================
CREATE TABLE IF NOT EXISTS misinfo_flags (
    id              SERIAL PRIMARY KEY,
    post_id         INTEGER NOT NULL REFERENCES processed_posts(id) ON DELETE CASCADE,
    claim_text      TEXT NOT NULL,
    flag_reason     VARCHAR(500),
    confidence      FLOAT DEFAULT 0.0,
    flagged_at      TIMESTAMPTZ DEFAULT NOW(),
    reviewed        BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_misinfo_flags_post_id ON misinfo_flags(post_id);
CREATE INDEX idx_misinfo_flags_confidence ON misinfo_flags(confidence);

-- ============================================================
-- Table: drug_ae_graph
-- Stores knowledge graph edges between drugs and adverse events
-- ============================================================
CREATE TABLE IF NOT EXISTS drug_ae_graph (
    id              SERIAL PRIMARY KEY,
    drug_name       VARCHAR(100) NOT NULL,
    ae_term         VARCHAR(200) NOT NULL,
    edge_weight     INTEGER DEFAULT 1,
    first_detected  TIMESTAMPTZ DEFAULT NOW(),
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(drug_name, ae_term)
);

CREATE INDEX idx_drug_ae_graph_drug_name ON drug_ae_graph(drug_name);
CREATE INDEX idx_drug_ae_graph_ae_term ON drug_ae_graph(ae_term);

-- ============================================================
-- Table: drug_stats_cache
-- Stores pre-computed per-drug statistics for fast dashboard loads
-- ============================================================
CREATE TABLE IF NOT EXISTS drug_stats_cache (
    id              SERIAL PRIMARY KEY,
    drug_name       VARCHAR(100) UNIQUE NOT NULL,
    total_posts     INTEGER DEFAULT 0,
    top_ae_json     JSONB,
    avg_sentiment   FLOAT DEFAULT 0.0,
    last_computed   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Table: ingestion_log
-- Tracks which .zst files have been loaded to prevent duplicates
-- ============================================================
CREATE TABLE IF NOT EXISTS ingestion_log (
    id              SERIAL PRIMARY KEY,
    filename        VARCHAR(255) NOT NULL,
    records_read    INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          VARCHAR(50) DEFAULT 'pending'
);

CREATE INDEX idx_ingestion_log_filename ON ingestion_log(filename);
CREATE INDEX idx_ingestion_log_status ON ingestion_log(status);
