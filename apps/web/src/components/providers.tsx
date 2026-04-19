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
      <Toaster
        position="top-right"
        expand={false}
        richColors
        closeButton
        theme="dark"
        toastOptions={{
          style: {
            background: '#1a1a2e',
            border: '1px solid #2a2a4a',
            color: '#fff',
          },
        }}
      />
    </HeroUIProvider>
    </QueryClientProvider>
  )
}
