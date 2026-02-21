import { DashboardHeader } from "@/components/dashboard/header"
import { KpiCards } from "@/components/dashboard/kpi-cards"
import { AdvisorsPanel } from "@/components/dashboard/advisors-panel"
import { TransactionsTable } from "@/components/dashboard/transactions-table"
import { FeeHistogram } from "@/components/dashboard/fee-histogram"
import { StatusBar } from "@/components/dashboard/status-bar"

export default function Page() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <DashboardHeader />

      <main className="flex flex-1 flex-col gap-6 px-6 py-6 lg:px-10 lg:py-8">
        {/* KPI Row */}
        <section aria-label="Key metrics">
          <KpiCards />
        </section>

        {/* Middle Row: Advisors + Fee Histogram */}
        <section
          className="grid grid-cols-1 gap-6 lg:grid-cols-3"
          aria-label="Advisors and fee distribution"
        >
          <div className="lg:col-span-2">
            <AdvisorsPanel />
          </div>
          <div>
            <FeeHistogram />
          </div>
        </section>

        {/* Data Table */}
        <section aria-label="Transaction data">
          <TransactionsTable />
        </section>
      </main>

      <StatusBar />
    </div>
  )
}
