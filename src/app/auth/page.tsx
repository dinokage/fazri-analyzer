import React from 'react'
import { redirect } from "next/navigation"
import { getServerSession } from "next-auth/next"
import SigninPage from '@/components/auth/SigninForm';
import { Metadata } from 'next';

export const metadata:Metadata = {
  title: `Sign In `,
};

const page = async() => {
  const session = await getServerSession()
  if(session){
    redirect('/dashboard')
  }
  return (
    <SigninPage />
  )
}

export default page