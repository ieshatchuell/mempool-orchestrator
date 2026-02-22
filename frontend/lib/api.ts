/**
 * Centralized API client for the FastAPI backend.
 *
 * All endpoint URLs derive from NEXT_PUBLIC_API_URL (set in .env.local).
 * Zero hardcoded URLs. Typed return values from lib/types.ts.
 */

import type {
    MempoolStats,
    FeeDistribution,
    RecentBlocks,
    Watchlist,
    OrchestratorStatus,
} from "./types";

const CLIENT_API_URL =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SERVER_API_URL =
    process.env.INTERNAL_API_URL ?? "http://host.docker.internal:8000";

/**
 * Resolve API base URL based on execution context.
 * - Server (SSR inside Docker): uses host.docker.internal to reach the host.
 * - Client (browser): uses localhost as configured in NEXT_PUBLIC_API_URL.
 */
function getBaseUrl(): string {
    if (typeof window === "undefined") return SERVER_API_URL;
    return CLIENT_API_URL;
}

/**
 * Generic typed fetch wrapper with error handling.
 * Throws on non-2xx responses with the status code and path.
 */
async function fetchAPI<T>(path: string): Promise<T> {
    const res = await fetch(`${getBaseUrl()}${path}`, { cache: "no-store" });
    if (!res.ok) {
        throw new Error(`API error ${res.status}: ${path}`);
    }
    return res.json() as Promise<T>;
}

export const api = {
    getMempoolStats: () =>
        fetchAPI<MempoolStats>("/api/mempool/stats"),

    getFeeDistribution: () =>
        fetchAPI<FeeDistribution>("/api/mempool/fee-distribution"),

    getRecentBlocks: (limit = 10) =>
        fetchAPI<RecentBlocks>(`/api/blocks/recent?limit=${limit}`),

    getWatchlist: () =>
        fetchAPI<Watchlist>("/api/watchlist"),

    getOrchestratorStatus: () =>
        fetchAPI<OrchestratorStatus>("/api/orchestrator/status"),
};
