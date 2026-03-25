"use client";

import { useSession } from "@/lib/auth-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FullscreenLoader } from "@/components/fullscreen-loader";

export default function ProfilePage() {
  const { data: session, isPending } = useSession();

  if (isPending) return <FullscreenLoader />;

  const user = session?.user as Record<string, unknown> | undefined;
  if (!user) return null;

  const name = String(user.name ?? "");
  const email = String(user.email ?? "");
  const role = String(user.role ?? "");
  const entity_id = String(user.entity_id ?? "");
  const face_id = user.face_id ? String(user.face_id) : null;
  const student_id = user.student_id ? String(user.student_id) : null;
  const staff_id = user.staff_id ? String(user.staff_id) : null;
  const department = user.department ? String(user.department) : null;

  return (
    <div className="container mx-auto max-w-2xl py-10 px-4">
      <Card className="shadow-lg border border-border rounded-2xl">
        <CardHeader className="flex flex-col items-center text-center">
          <Avatar className="h-20 w-20 mb-3">
            <AvatarImage
              src={`https://cdn.hextasphere.com/hexta/ethos/${face_id}.jpg`}
              alt={name}
            />
            <AvatarFallback>
              {name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <CardTitle className="text-2xl font-semibold">{name}</CardTitle>
          <Badge variant="secondary" className="mt-2 text-sm">
            {role}
          </Badge>
        </CardHeader>

        <Separator />

        <CardContent className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{email}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-muted-foreground">Entity ID</span>
            <span className="font-medium">{entity_id}</span>
          </div>

          {role === "STUDENT" && student_id && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Student ID</span>
              <span className="font-medium">{student_id}</span>
            </div>
          )}

          {role === "STAFF" && staff_id && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Staff ID</span>
              <span className="font-medium">{staff_id}</span>
            </div>
          )}

          {department && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Department</span>
              <span className="font-medium">{department}</span>
            </div>
          )}

          <div className="flex justify-between">
            <span className="text-muted-foreground">Face ID</span>
            <span className="font-medium">{face_id ?? "Not linked"}</span>
          </div>
        </CardContent>

        <div className="px-6 pb-6 mt-2">
          <Button className="w-full">Edit Profile</Button>
        </div>
      </Card>
    </div>
  );
}
