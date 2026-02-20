"use client"

import { BarChart3 } from "lucide-react"

const feeBands = [
  { range: "1-5", count: 12847, pct: 18 },
  { range: "5-10", count: 8921, pct: 13 },
  { range: "10-15", count: 14203, pct: 20 },
  { range: "15-20", count: 18472, pct: 26 },
  { range: "20-30", count: 9184, pct: 13 },
  { range: "30-50", count: 4219, pct: 6 },
  { range: "50+", count: 2841, pct: 4 },
]

export function FeeHistogram() {
  const maxPct = Math.max(...feeBands.map((b) => b.pct))

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
          70,687 txs
        </span>
      </div>

      <div className="px-5 py-4">
        <div className="flex flex-col gap-2.5">
          {feeBands.map((band) => {
            const isPeak = band.pct === maxPct

            return (
              <div key={band.range} className="flex items-center gap-3">
                <span className="w-10 text-right font-mono text-xs tabular-nums text-muted-foreground">
                  {band.range}
                </span>
                <div className="flex h-5 flex-1 items-center overflow-hidden rounded-md bg-muted">
                  <div
                    className={`h-full rounded-md transition-all duration-500 ${
                      isPeak ? "bg-bitcoin" : "bg-info/60"
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

        <div className="mt-4 flex items-center gap-2 rounded-xl bg-bitcoin-soft px-3 py-2">
          <span className="text-xs text-muted-foreground">Peak band</span>
          <span className="font-mono text-xs font-semibold text-bitcoin">
            15-20 sat/vB
          </span>
          <span className="text-xs text-muted-foreground">
            (26% of mempool)
          </span>
        </div>
      </div>
    </div>
  )
}
