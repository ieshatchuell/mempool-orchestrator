"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, type ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n/context";

/**
 * Client-side providers for TanStack Query + i18n.
 *
 * QueryClient is created once per component lifecycle (useState initializer).
 * I18nProvider exposes locale / dictionary / setLocale to all children.
 * DevTools panel is available in development builds only.
 */
export function Providers({ children }: { children: ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        retry: 3,
                        refetchOnWindowFocus: true,
                    },
                },
            }),
    );

    return (
        <QueryClientProvider client={queryClient}>
            <I18nProvider>{children}</I18nProvider>
            <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
    );
}
