import React from 'react'
import { redirect } from "next/navigation"
import { getAuthSession } from '@/lib/auth-server'
import { headers } from 'next/headers'
import SigninPage from '@/components/auth/SigninForm';
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Sign In `,
};

const page = async() => {
  const session = await getAuthSession(await headers())
  if (session) {
    redirect('/dashboard')
  }
  return (
    <SigninPage />
  )
}

export default page