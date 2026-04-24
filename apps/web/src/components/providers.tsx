"use client"
import { useState } from 'react'
import {HeroUIProvider} from '@heroui/react'
import { Toaster } from 'sonner'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

export function Providers({children}: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        // Prevent all queries from refetching the moment the user switches
        // back to the tab. Alert polling uses its own refetchInterval and is
        // unaffected; this only stops the on-focus cascade.
        refetchOnWindowFocus: false,
        // Reduce noise: one retry is enough before surfacing an error.
        retry: 1,
        retryDelay: 2000,
      },
    },
  }))
  return (
    <QueryClientProvider client={queryClient}>
    <HeroUIProvider>
      {children}
      <Toaster position="bottom-right" />
    </HeroUIProvider>
    </QueryClientProvider>
  )
}
