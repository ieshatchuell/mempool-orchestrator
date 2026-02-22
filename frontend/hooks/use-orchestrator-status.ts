import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { OrchestratorStatus } from "@/lib/types";

/**
 * Strategy engine state: mode, fees, EMA, traffic level.
 * Polls every 10s — EMA and traffic move with mempool stats.
 */
export function useOrchestratorStatus() {
    return useQuery<OrchestratorStatus>({
        queryKey: ["orchestrator", "status"],
        queryFn: api.getOrchestratorStatus,
        refetchInterval: 10_000,
        staleTime: 8_000,
    });
}
