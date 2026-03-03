"use client"

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from "recharts"
import { useRecentBlocks } from "@/hooks/use-recent-blocks"
import { AlertCircle, BarChart3 } from "lucide-react"

// ── Types ───────────────────────────────────────────────────────

interface FeeBarDatum {
    label: string
    value: number
}

const PERCENTILE_LABELS = ["Min", "P10", "P25", "P50", "P75", "P90", "Max"]

const BAR_COLORS = [
    "var(--success)",        // Min  — green (cheap)
    "var(--chart-3)",        // P10
    "var(--info)",           // P25
    "var(--bitcoin)",        // P50  — Bitcoin gold (median)
    "var(--warning)",        // P75
    "var(--chart-4)",        // P90
    "var(--destructive)",    // Max  — red (expensive)
]

// ── Skeleton ────────────────────────────────────────────────────

function HistogramSkeleton() {
    return (
        <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 animate-pulse">
            <div className="flex items-center justify-between">
                <div className="h-4 w-32 rounded bg-muted" />
                <div className="h-4 w-16 rounded bg-muted" />
            </div>
            <div className="h-[200px] rounded bg-muted" />
        </div>
    )
}

// ── Custom Tooltip ──────────────────────────────────────────────

function CustomTooltip({
    active,
    payload,
    label,
}: {
    active?: boolean
    payload?: Array<{ value: number }>
    label?: string
}) {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-lg border border-border bg-card px-3 py-2 shadow-lg">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="font-mono text-sm font-semibold text-foreground">
                {payload[0].value.toFixed(2)}{" "}
                <span className="text-xs font-normal text-muted-foreground">
                    sat/vB
                </span>
            </p>
        </div>
    )
}

// ── Main Component ──────────────────────────────────────────────

export function FeeHistogram() {
    const { data, isError } = useRecentBlocks()

    if (isError) {
        return (
            <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span>Unable to load fee distribution</span>
            </div>
        )
    }

    if (!data) return <HistogramSkeleton />

    // Use the latest block's fee_range for the histogram
    const latestBlock = data.blocks[0]
    const feeRange = latestBlock?.fee_range ?? []

    // Build chart data from the 7-band array
    const chartData: FeeBarDatum[] = PERCENTILE_LABELS.map((label, i) => ({
        label,
        value: feeRange[i] ?? 0,
    }))

    const hasData = chartData.some((d) => d.value > 0)

    return (
        <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none animate-fade-in-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-bitcoin" />
                    <h2 className="text-sm font-semibold text-foreground">
                        Fee Distribution
                    </h2>
                </div>
                {latestBlock && (
                    <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                        Block #{latestBlock.height.toLocaleString()}
                    </span>
                )}
            </div>

            {/* Chart */}
            {!hasData ? (
                <div className="flex h-[200px] items-center justify-center text-xs text-muted-foreground">
                    No fee distribution data available
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                        data={chartData}
                        margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
                    >
                        <XAxis
                            dataKey="label"
                            tick={{
                                fontSize: 11,
                                fill: "var(--muted-foreground)",
                            }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            tick={{
                                fontSize: 10,
                                fill: "var(--muted-foreground)",
                            }}
                            tickLine={false}
                            axisLine={false}
                            width={40}
                            tickFormatter={(v: number) => v.toFixed(1)}
                        />
                        <Tooltip
                            content={<CustomTooltip />}
                            cursor={{ fill: "var(--muted)", opacity: 0.3 }}
                        />
                        <Bar
                            dataKey="value"
                            radius={[6, 6, 0, 0]}
                            maxBarSize={36}
                        >
                            {chartData.map((_, i) => (
                                <Cell
                                    key={i}
                                    fill={BAR_COLORS[i]}
                                    opacity={0.85}
                                />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            )}

            {/* Legend */}
            <div className="flex items-center justify-center gap-3 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                    <span
                        className="inline-block h-2 w-2 rounded-sm"
                        style={{ backgroundColor: "var(--success)" }}
                    />
                    Cheap
                </span>
                <span className="flex items-center gap-1">
                    <span
                        className="inline-block h-2 w-2 rounded-sm"
                        style={{ backgroundColor: "var(--bitcoin)" }}
                    />
                    Median
                </span>
                <span className="flex items-center gap-1">
                    <span
                        className="inline-block h-2 w-2 rounded-sm"
                        style={{ backgroundColor: "var(--destructive)" }}
                    />
                    Premium
                </span>
            </div>
        </div>
    )
}
