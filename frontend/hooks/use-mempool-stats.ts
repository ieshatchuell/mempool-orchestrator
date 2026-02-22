import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MempoolStats } from "@/lib/types";

/**
 * KPI card data: mempool size, fees, blocks to clear, 1h deltas.
 * Polls every 5s — highest frequency because KPIs are the most volatile signal.
 */
export function useMempoolStats() {
    return useQuery<MempoolStats>({
        queryKey: ["mempool", "stats"],
        queryFn: api.getMempoolStats,
        refetchInterval: 5_000,
        staleTime: 3_000,
    });
}
