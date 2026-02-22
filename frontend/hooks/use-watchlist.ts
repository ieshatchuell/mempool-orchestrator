import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Watchlist } from "@/lib/types";

/**
 * Tracked transactions with RBF/CPFP advisory info.
 * Polls every 15s — advisories are recalculated on each storage flush.
 */
export function useWatchlist() {
    return useQuery<Watchlist>({
        queryKey: ["watchlist"],
        queryFn: api.getWatchlist,
        refetchInterval: 15_000,
        staleTime: 12_000,
    });
}
