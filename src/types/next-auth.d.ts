import { DefaultSession } from "next-auth";
import { UserRole } from "@prisma/client"; // <<< Ensure this import is correct

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      entity_id: string; // From your User model
      name?: string | null;
      email?: string | null;
      role?: UserRole;    // <--- This needs to be UserRole type
      face_id?: string | null;
    } & DefaultSession["user"];
  }

  interface User { // This is the 'user' object returned from `authorize`
    id: string;
    entity_id: string;
    name?: string | null;
    email?: string | null;
    role?: UserRole;    // <--- This needs to be UserRole type
    face_id?: string | null;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    entity_id: string;
    name?: string | null;
    email?: string | null;
    role?: UserRole;    // <--- This needs to be UserRole type
    face_id?: string | null;
  }
}