"use client"

import { Box } from "lucide-react"
import { useTranslations } from "@/hooks/use-translations"

/**
 * Translatable section headers extracted from page.tsx.
 *
 * This is a client component because it uses the i18n context.
 * The page component itself remains a server component.
 */
export function SectionHeaders({ variant }: { variant: "live" | "settlement" }) {
  const { t } = useTranslations()

  if (variant === "live") {
    return (
      <h2 className="relative z-10 flex items-center gap-2.5 text-xl font-semibold tracking-tight text-foreground">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </span>
        {t.sections.liveMarket}
      </h2>
    )
  }

  return (
    <h2 className="flex items-center gap-2.5 text-xl font-semibold tracking-tight text-foreground">
      <Box className="h-4.5 w-4.5 text-muted-foreground" />
      {t.sections.settlementHistory}
    </h2>
  )
}
