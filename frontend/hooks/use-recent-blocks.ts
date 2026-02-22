import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RecentBlocks } from "@/lib/types";

/**
 * Confirmed blocks from block_history.
 * Polls every 30s — blocks are mined ~every 10 minutes.
 */
export function useRecentBlocks(limit = 10) {
    return useQuery<RecentBlocks>({
        queryKey: ["blocks", "recent", limit],
        queryFn: () => api.getRecentBlocks(limit),
        refetchInterval: 30_000,
        staleTime: 25_000,
    });
}
