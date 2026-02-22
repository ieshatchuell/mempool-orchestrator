/**
 * TypeScript interfaces for FastAPI response schemas.
 *
 * Mapped 1:1 from backend/src/api/schemas.py.
 * Monetary values: integers (Satoshis). Fee rates: floats (sat/vB).
 */

// ── /api/mempool/stats ──────────────────────────────────────────

export interface MempoolStats {
  mempool_size: number;
  mempool_bytes: number;
  total_fee_sats: number;
  median_fee: number;
  blocks_to_clear: number;
  delta_size_pct: number | null;
  delta_fee_pct: number | null;
}

// ── /api/mempool/fee-distribution ────────────────────────────────

export interface FeeBand {
  range: string;
  count: number;
  pct: number;
}

export interface FeeDistribution {
  bands: FeeBand[];
  total_txs: number;
  peak_band: string;
}

// ── /api/blocks/recent ──────────────────────────────────────────

export interface RecentBlock {
  height: number;
  timestamp: string;
  tx_count: number;
  size_bytes: number;
  median_fee: number;
  total_fees_sats: number;
  fee_range: number[];
  pool_name: string | null;
}

export interface RecentBlocks {
  blocks: RecentBlock[];
  latest_height: number | null;
}

// ── /api/watchlist ──────────────────────────────────────────────

export interface WatchlistAdvisory {
  txid: string;
  role: string;
  status: string;
  current_fee_rate: number | null;
  action: string;
  action_type: string;
  cost_sats: number | null;
}

export interface Watchlist {
  advisories: WatchlistAdvisory[];
  stuck_count: number;
  total_count: number;
}

// ── /api/orchestrator/status ────────────────────────────────────

export interface OrchestratorStatus {
  strategy_mode: string;
  current_median_fee: number;
  historical_median_fee: number;
  ema_fee: number;
  ema_trend: string;
  fee_premium_pct: number;
  traffic_level: string;
  latest_block_height: number | null;
}
