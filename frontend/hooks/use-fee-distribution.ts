import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FeeDistribution } from "@/lib/types";

/**
 * Fee histogram from projected mempool blocks.
 * Polls every 10s — fee distribution shifts slower than raw stats.
 */
export function useFeeDistribution() {
    return useQuery<FeeDistribution>({
        queryKey: ["mempool", "fee-distribution"],
        queryFn: api.getFeeDistribution,
        refetchInterval: 10_000,
        staleTime: 8_000,
    });
}
