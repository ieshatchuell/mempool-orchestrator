"use client"

import { BarChart3, AlertCircle } from "lucide-react"
import { useFeeDistribution } from "@/hooks/use-fee-distribution"

function HistogramSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="h-4 w-32 rounded bg-muted animate-pulse" />
        <div className="h-4 w-16 rounded bg-muted animate-pulse" />
      </div>
      <div className="flex flex-col gap-2.5 px-5 py-4">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="h-4 w-10 rounded bg-muted animate-pulse" />
            <div className="h-5 flex-1 rounded-md bg-muted animate-pulse" />
            <div className="h-4 w-8 rounded bg-muted animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function FeeHistogram() {
  const { data, isError } = useFeeDistribution()

  if (isError) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        <span>Unable to load fee distribution</span>
      </div>
    )
  }

  if (!data) return <HistogramSkeleton />

  const { bands, total_txs, peak_band } = data
  const maxPct = bands.length > 0 ? Math.max(...bands.map((b) => b.pct)) : 1

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2.5">
          <BarChart3 className="h-4 w-4 text-info" />
          <h2 className="text-sm font-semibold text-foreground">
            Fee Distribution
          </h2>
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          {total_txs.toLocaleString()} txs
        </span>
      </div>

      <div className="px-5 py-4">
        <div className="flex flex-col gap-2.5">
          {bands.map((band) => {
            const isPeak = band.pct === maxPct

            return (
              <div key={band.range} className="flex items-center gap-3">
                <span className="w-10 text-right font-mono text-xs tabular-nums text-muted-foreground">
                  {band.range}
                </span>
                <div className="flex h-5 flex-1 items-center overflow-hidden rounded-md bg-muted">
                  <div
                    className={`h-full rounded-md transition-all duration-500 ${isPeak ? "bg-bitcoin" : "bg-info/60"
                      }`}
                    style={{
                      width: `${(band.pct / maxPct) * 100}%`,
                    }}
                  />
                </div>
                <span className="w-8 text-right font-mono text-xs font-medium tabular-nums text-foreground">
                  {band.pct}%
                </span>
              </div>
            )
          })}
        </div>

        {bands.length > 0 && (
          <div className="mt-4 flex items-center gap-2 rounded-xl bg-bitcoin-soft px-3 py-2">
            <span className="text-xs text-muted-foreground">Peak band</span>
            <span className="font-mono text-xs font-semibold text-bitcoin">
              {peak_band} sat/vB
            </span>
            <span className="text-xs text-muted-foreground">
              ({maxPct}% of mempool)
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
