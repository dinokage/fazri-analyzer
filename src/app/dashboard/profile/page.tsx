import { getServerSession } from "next-auth";
import { OPTIONS } from "@/auth";
import { redirect } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: `Profile `,
};

export default async function ProfilePage() {
  const session = await getServerSession(OPTIONS);

  if (!session || !session.user) {
    redirect("/auth");
  }

  const user = session.user as {
    name: string;
    email: string;
    id: string;
    entity_id: string;
    role: string;
    face_id: string | null;
    student_id: string | null;
    staff_id: string | null;
    department: string | null;
  };

  return (
    <div className="container mx-auto max-w-2xl py-10 px-4">
      <Card className="shadow-lg border border-border rounded-2xl">
        <CardHeader className="flex flex-col items-center text-center">
          <Avatar className="h-20 w-20 mb-3">
            <AvatarImage src={`https://cdn.hextasphere.com/ethos/${user.face_id}.jpg`} alt={user.name} />
            <AvatarFallback>
              {user.name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <CardTitle className="text-2xl font-semibold">{user.name}</CardTitle>
          <Badge variant="secondary" className="mt-2 text-sm">
            {user.role}
          </Badge>
        </CardHeader>

        <Separator />

        <CardContent className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user.email}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-muted-foreground">Entity ID</span>
            <span className="font-medium">{user.entity_id}</span>
          </div>

          {user.role === "STUDENT" && user.student_id && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Student ID</span>
              <span className="font-medium">{user.student_id}</span>
            </div>
          )}

          {user.role === "STAFF" && user.staff_id && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Staff ID</span>
              <span className="font-medium">{user.staff_id}</span>
            </div>
          )}

          {user.department && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Department</span>
              <span className="font-medium">{user.department}</span>
            </div>
          )}

          <div className="flex justify-between">
            <span className="text-muted-foreground">Face ID</span>
            <span className="font-medium">{user.face_id || "Not linked"}</span>
          </div>
        </CardContent>

        <div className="px-6 pb-6 mt-2">
          <Button className="w-full">Edit Profile</Button>
        </div>
      </Card>
    </div>
  );
}
