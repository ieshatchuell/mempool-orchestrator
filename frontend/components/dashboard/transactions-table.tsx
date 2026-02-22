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
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_1px_3px_rgba(0,0,0,0.04)] dark:shadow-none">
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
                  <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">
                    {formatFeeRange(block.fee_range)}
                    <span className="text-muted-foreground/60"> sat/vB</span>
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
                      <span className="text-sm text-foreground">
                        {block.pool_name ?? "Unknown"}
                      </span>
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
