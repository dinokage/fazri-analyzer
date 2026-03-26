export type UserRole = "STUDENT" | "STAFF" | "FACULTY" | "SUPER_ADMIN";

export interface FazriUser {
  id: string;
  name: string;
  email: string;
  image?: string | null;
  entity_id: string;
  username: string;
  role: UserRole;
  face_id?: string | null;
  student_id?: string | null;
  staff_id?: string | null;
  department?: string | null;
  card_id?: string | null;
  device_hash?: string | null;
}

export interface FazriSession {
  user: FazriUser;
  session: {
    id: string;
    token: string;
    expiresAt: string;
    userId: string;
  };
}
