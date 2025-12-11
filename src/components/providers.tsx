"use client"
import {HeroUIProvider} from '@heroui/react'
import { Toaster } from 'sonner'

export function Providers({children}: { children: React.ReactNode }) {
  return (
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
  )
}