import { DashboardHeader } from "@/components/dashboard/header"
import { KpiCards } from "@/components/dashboard/kpi-cards"
import { FeeHistogram } from "@/components/dashboard/fee-histogram"
import { BlockWeightChart } from "@/components/dashboard/block-weight-chart"
import { AdvisorsPanel } from "@/components/dashboard/advisors-panel"
import { TransactionsTable } from "@/components/dashboard/transactions-table"
import { StrategyPanel } from "@/components/dashboard/strategy-panel"
import { StatusBar } from "@/components/dashboard/status-bar"
import { SectionHeaders } from "@/components/dashboard/section-headers"
import { Separator } from "@/components/ui/separator"

export default function Page() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <DashboardHeader />

      <main className="relative flex flex-1 flex-col gap-6 px-6 py-6 lg:px-10 lg:py-8">
        {/* ── Indigo glow — Live Market zone ── */}
        <div
          className="pointer-events-none absolute inset-x-0 top-0 z-0 h-[600px]"
          aria-hidden="true"
          style={{
            background:
              "radial-gradient(ellipse 80% 50% at 50% -5%, rgba(99,102,241,0.35) 0%, rgba(99,102,241,0.12) 40%, transparent 70%)",
          }}
        />

        {/* ── Section 1: Live Market Dynamics ── */}
        <SectionHeaders variant="live" />

        {/* KPI Row */}
        <section className="relative z-10" aria-label="Key metrics">
          <KpiCards />
        </section>

        {/* Advisors + Strategy Panel */}
        <section
          className="relative z-10 grid grid-cols-1 gap-6 lg:grid-cols-3"
          aria-label="Advisors and strategy"
        >
          <div className="lg:col-span-2">
            <AdvisorsPanel />
          </div>
          <div>
            <StrategyPanel />
          </div>
        </section>

        {/* ── Separator ── */}
        <Separator className="relative z-10 mt-8" />

        {/* ── Section 2: Settlement History ── */}
        <div className="relative">
          <div className="relative z-10 flex flex-col gap-6">
            <SectionHeaders variant="settlement" />

            {/* Analytics Row: Fee Distribution + Block Weight */}
            <section
              className="grid grid-cols-1 gap-6 lg:grid-cols-2"
              aria-label="Analytics charts"
            >
              <FeeHistogram />
              <BlockWeightChart />
            </section>

            {/* Recent Blocks Table */}
            <section aria-label="Transaction data">
              <TransactionsTable />
            </section>
          </div>
        </div>
      </main>

      <StatusBar />
    </div>
  )
}
