"use client"

import { useRecentBlocks } from "@/hooks/use-recent-blocks"
import { AlertCircle, Box } from "lucide-react"

// ── Constants ───────────────────────────────────────────────────

/** Max block weight in Weight Units (BIP-141) */
const MAX_BLOCK_WEIGHT = 4_000_000

/** Approximate max block size in bytes (SegWit worst-case) */
const MAX_BLOCK_SIZE = 4_000_000

// ── Types ───────────────────────────────────────────────────────

interface BlockBar {
    height: number
    sizeBytes: number
    fullnessPct: number
    txCount: number
    poolName: string
    medianFee: number
}

// ── Skeleton ────────────────────────────────────────────────────

function WeightChartSkeleton() {
    return (
        <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 animate-pulse">
            <div className="flex items-center justify-between">
                <div className="h-4 w-32 rounded bg-muted" />
                <div className="h-4 w-16 rounded bg-muted" />
            </div>
            <div className="flex flex-col gap-2">
                {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="h-6 rounded bg-muted" />
                ))}
            </div>
        </div>
    )
}

// ── Fullness Color ──────────────────────────────────────────────

function getFullnessColor(pct: number): string {
    if (pct >= 90) return "bg-success"
    if (pct >= 70) return "bg-bitcoin"
    return "bg-muted-foreground/40"
}

function getFullnessLabel(pct: number): string {
    if (pct >= 95) return "Full"
    if (pct >= 80) return "Heavy"
    if (pct >= 50) return "Normal"
    return "Light"
}

// ── Size Formatter ──────────────────────────────────────────────

function formatSize(bytes: number): string {
    if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(2)} MB`
    if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`
    return `${bytes} B`
}

// ── Block Bar Row ───────────────────────────────────────────────

function BlockBarRow({ block }: { block: BlockBar }) {
    return (
        <div className="group flex items-center gap-3">
            {/* Height label */}
            <span className="w-16 shrink-0 text-right font-mono text-xs tabular-nums text-muted-foreground">
                {block.height.toLocaleString()}
            </span>

            {/* Bar container */}
            <div className="relative flex h-7 flex-1 items-center overflow-hidden rounded-lg bg-muted/50">
                {/* Filled portion */}
                <div
                    className={`absolute inset-y-0 left-0 rounded-lg transition-all duration-500 ${getFullnessColor(block.fullnessPct)}`}
                    style={{ width: `${Math.min(block.fullnessPct, 100)}%`, opacity: 0.2 }}
                />
                <div
                    className={`absolute inset-y-0 left-0 rounded-lg transition-all duration-500 ${getFullnessColor(block.fullnessPct)}`}
                    style={{ width: `${Math.min(block.fullnessPct, 100)}%`, opacity: 0.6, maxWidth: "calc(100% - 1px)" }}
                />

                {/* Bar content overlay */}
                <div className="relative z-10 flex w-full items-center justify-between px-2.5">
                    <div className="flex items-center gap-2">
                        {/* Pool badge */}
                        <span className="rounded-md bg-card/80 px-1.5 py-0.5 text-[10px] font-medium text-foreground shadow-sm backdrop-blur-sm">
                            {block.poolName}
                        </span>
                        <span className="text-[10px] text-foreground/60">
                            {block.txCount.toLocaleString()} txs
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-foreground/60">
                            {formatSize(block.sizeBytes)}
                        </span>
                        <span className="rounded-md bg-card/80 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-foreground shadow-sm backdrop-blur-sm">
                            {block.fullnessPct.toFixed(0)}%
                        </span>
                    </div>
                </div>
            </div>

            {/* Fullness label */}
            <span className="w-12 shrink-0 text-[10px] font-medium text-muted-foreground">
                {getFullnessLabel(block.fullnessPct)}
            </span>
        </div>
    )
}

// ── Main Component ──────────────────────────────────────────────

export function BlockWeightChart() {
    const { data, isError } = useRecentBlocks()

    if (isError) {
        return (
            <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span>Unable to load block data</span>
            </div>
        )
    }

    if (!data) return <WeightChartSkeleton />

    const { blocks } = data

    // Build block bars (latest first)
    const blockBars: BlockBar[] = blocks.map((b) => ({
        height: b.height,
        sizeBytes: b.size_bytes,
        fullnessPct: (b.size_bytes / MAX_BLOCK_SIZE) * 100,
        txCount: b.tx_count,
        poolName: b.pool_name ?? "Unknown",
        medianFee: b.median_fee,
    }))

    return (
        <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none animate-fade-in-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Box className="h-4 w-4 text-info" />
                    <h2 className="text-sm font-semibold text-foreground">
                        Block Weight
                    </h2>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <span className="inline-block h-2 w-2 rounded-sm bg-success" />
                        &gt;90%
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="inline-block h-2 w-2 rounded-sm bg-bitcoin" />
                        70-90%
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="inline-block h-2 w-2 rounded-sm bg-muted-foreground/40" />
                        &lt;70%
                    </span>
                </div>
            </div>

            {/* Block bars */}
            {blockBars.length === 0 ? (
                <div className="flex h-[180px] items-center justify-center text-xs text-muted-foreground">
                    No block data available
                </div>
            ) : (
                <div className="flex flex-col gap-1.5">
                    {blockBars.map((block) => (
                        <BlockBarRow key={block.height} block={block} />
                    ))}
                </div>
            )}
        </div>
    )
}
