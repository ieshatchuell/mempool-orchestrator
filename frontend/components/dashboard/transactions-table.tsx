"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  CheckCircle2,
  ExternalLink,
  Box,
  AlertCircle,
} from "lucide-react"
import { useRecentBlocks } from "@/hooks/use-recent-blocks"

function formatSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(2)} MB`
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`
  return `${bytes} B`
}

function formatBtc(sats: number): string {
  return (sats / 100_000_000).toFixed(4)
}

function formatFeeRange(range: number[]): string {
  if (!range || range.length === 0) return "N/A"
  const min = Math.round(range[0])
  const max = Math.round(range[range.length - 1])
  return `${min} - ${max}`
}

function FeeRangeMiniBar({ range }: { range: number[] }) {
  if (!range || range.length < 2) return null
  const min = range[0]
  const max = range[range.length - 1]
  if (max === 0) return null

  return (
    <div className="mt-1 h-1 w-full max-w-[80px] overflow-hidden rounded-full bg-muted">
      <div
        className="h-full rounded-full"
        style={{
          width: `${Math.min(100, (min / max) * 100 + 20)}%`,
          background: `linear-gradient(90deg, var(--success) 0%, var(--bitcoin) 50%, var(--destructive) 100%)`,
          opacity: 0.7,
        }}
      />
    </div>
  )
}

const POOL_COLORS: Record<string, string> = {
  "Foundry USA": "bg-blue-500",
  "AntPool": "bg-orange-500",
  "ViaBTC": "bg-green-500",
  "F2Pool": "bg-purple-500",
  "Binance Pool": "bg-yellow-500",
  "MARA Pool": "bg-red-500",
  "SpiderPool": "bg-cyan-500",
}

function PoolBadge({ name }: { name: string | null }) {
  const poolName = name ?? "Unknown"
  const dotColor = POOL_COLORS[poolName] ?? "bg-muted-foreground/40"

  return (
    <div className="flex items-center gap-1.5">
      <span className={`inline-block h-2 w-2 rounded-full ${dotColor}`} />
      <span className="text-sm text-foreground">{poolName}</span>
    </div>
  )
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString("en-US", { hour12: false })
  } catch {
    return iso
  }
}

function BlocksTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="h-8 w-32 rounded bg-muted animate-pulse" />
        <div className="h-4 w-20 rounded bg-muted animate-pulse" />
      </div>
      <div className="p-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex gap-4 py-3">
            <div className="h-4 w-20 rounded bg-muted animate-pulse" />
            <div className="h-4 w-16 rounded bg-muted animate-pulse" />
            <div className="h-4 flex-1 rounded bg-muted animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function TransactionsTable() {
  const { data, isError } = useRecentBlocks()

  if (isError) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        <span>Unable to load recent blocks</span>
      </div>
    )
  }

  if (!data) return <BlocksTableSkeleton />

  const { blocks } = data

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none animate-fade-in-up">
      {/* Table Header */}
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex overflow-hidden rounded-xl border border-border bg-muted p-0.5">
            <div className="flex items-center gap-1.5 rounded-lg bg-card px-4 py-1.5 text-sm font-medium text-foreground shadow-sm">
              <Box className="h-3.5 w-3.5" />
              Recent Blocks
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-xs text-muted-foreground">
            {blocks.length} blocks
          </span>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          <span className="text-xs font-medium text-success">Live</span>
        </div>
      </div>

      {/* Blocks Table */}
      {blocks.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-muted-foreground">
          No confirmed blocks yet. Waiting for data...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Height
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Time
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Transactions
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Size
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Fee Range
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Median Fee
                </TableHead>
                <TableHead className="text-right text-xs font-medium text-muted-foreground">
                  Total Fees
                </TableHead>
                <TableHead className="text-xs font-medium text-muted-foreground">
                  Miner
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {blocks.map((block, i) => (
                <TableRow
                  key={block.height}
                  className="border-border transition-colors hover:bg-muted/50"
                >
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                      <span className="font-mono text-sm font-medium tabular-nums text-foreground">
                        {block.height.toLocaleString()}
                      </span>
                      {i === 0 && (
                        <span className="rounded-full bg-success-soft px-2 py-0.5 text-[10px] font-semibold text-success">
                          Latest
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm tabular-nums text-muted-foreground">
                    {formatTime(block.timestamp)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {block.tx_count.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {formatSize(block.size_bytes)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex flex-col items-end">
                      <span className="font-mono text-sm tabular-nums text-muted-foreground">
                        {formatFeeRange(block.fee_range)}
                        <span className="text-muted-foreground/60"> sat/vB</span>
                      </span>
                      <FeeRangeMiniBar range={block.fee_range} />
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className="font-mono text-sm font-medium tabular-nums text-bitcoin">
                      {block.median_fee.toFixed(1)}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {" "}
                      sat/vB
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums text-foreground">
                    {formatBtc(block.total_fees_sats)}
                    <span className="text-muted-foreground"> BTC</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <PoolBadge name={block.pool_name} />
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground/40 transition-colors hover:text-muted-foreground" />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
