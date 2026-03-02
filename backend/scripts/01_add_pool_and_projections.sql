-- =============================================================================
-- Session 6: Phase 6.5 — UI Polish
-- =============================================================================
-- Migration: Add pool_name and fee_range to blocks, create projections table.
--
-- Usage:
--   docker exec -i postgres psql -U mempool -d mempool < backend/scripts/01_add_pool_and_projections.sql
-- =============================================================================

-- 1. Enrich blocks table with mining pool name and fee distribution
ALTER TABLE blocks ADD COLUMN IF NOT EXISTS pool_name VARCHAR(64);
ALTER TABLE blocks ADD COLUMN IF NOT EXISTS fee_range JSONB;

-- 2. Create mempool block projections table (snapshot pattern)
CREATE TABLE IF NOT EXISTS mempool_block_projections (
    id SERIAL PRIMARY KEY,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    block_index INTEGER NOT NULL,
    block_size INTEGER NOT NULL,
    block_v_size DOUBLE PRECISION NOT NULL,
    n_tx INTEGER NOT NULL,
    total_fees BIGINT NOT NULL,
    median_fee DOUBLE PRECISION NOT NULL,
    fee_range JSONB
);
