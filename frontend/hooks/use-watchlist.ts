import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Watchlist } from "@/lib/types";

/**
 * Tracked transactions with dual RBF/CPFP advisory info.
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

/**
 * Add a TXID to the watchlist. Invalidates watchlist cache on success.
 */
export function useAddWatchlistTx() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (txid: string) => api.addWatchlistTx(txid),
        onSuccess: () => {
            return queryClient.invalidateQueries({ queryKey: ["watchlist"] });
        },
    });
}

/**
 * Remove a TXID from the watchlist. Invalidates watchlist cache on success.
 */
export function useRemoveWatchlistTx() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (txid: string) => api.removeWatchlistTx(txid),
        onSuccess: () => {
            return queryClient.invalidateQueries({ queryKey: ["watchlist"] });
        },
    });
}
