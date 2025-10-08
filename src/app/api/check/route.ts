
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
export async function POST(req: Request) {
  try {
    const { username } = await req.json();

    if (!username || typeof username !== 'string') {
      return NextResponse.json({ exists: false, error: 'Invalid username provided' }, { status: 400 });
    }

    const user = await prisma.user.findUnique({
      where: { entity_id: username },
    });

    return NextResponse.json({ exists: !!user }); // '!!user' converts user object to boolean
  } catch (error) {
    console.error('Error checking user existence:', error);
    return NextResponse.json({ exists: false, error: 'Internal server error' }, { status: 500 });
  }
}