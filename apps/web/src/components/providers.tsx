"use client"
import { useState } from 'react'
import {HeroUIProvider} from '@heroui/react'
import { Toaster } from 'sonner'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

export function Providers({children}: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient())
  return (
    <QueryClientProvider client={queryClient}>
    <HeroUIProvider>
      {children}
      <Toaster position="bottom-right" />
    </HeroUIProvider>
    </QueryClientProvider>
  )
}
