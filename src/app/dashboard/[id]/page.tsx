import { notFound } from "next/navigation"
import { getEntityById, getActivitiesByEntity } from "@/lib/entities"
import { Timeline } from "@/components/timeline"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export default function EntityDetailsPage({
  params,
}: {
  params: { id: string }
}) {
  const entity = getEntityById(params.id)
  if (!entity) return notFound()
  const activities = getActivitiesByEntity(params.id)

  const initials =
    entity.name
      .split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "NA"

  return (
    <div className="space-y-8">
      <div className="flex items-start gap-4">
        <Avatar className="size-16 md:size-20">
          <AvatarImage
            src={`/placeholder.svg?height=96&width=96&query=profile%20photo%20portrait`}
            alt={`${entity.name} profile photo`}
          />
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>

        <div className="min-w-0">
          <h2 className="text-2xl font-semibold text-pretty">
            {entity.name}
            <span className="ml-2 align-middle rounded-full border px-2 py-0.5 text-sm">{entity.role}</span>
          </h2>
          <p className="text-muted-foreground leading-relaxed">{entity.bio}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <dl className="grid gap-3">
          <div className="grid grid-cols-3 gap-2">
            <dt className="text-muted-foreground">Entity ID</dt>
            <dd className="col-span-2">{entity.id}</dd>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <dt className="text-muted-foreground">Enroll ID</dt>
            <dd className="col-span-2">{entity.enrollId}</dd>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <dt className="text-muted-foreground">Branch</dt>
            <dd className="col-span-2">{entity.branch}</dd>
          </div>
        </dl>

        <dl className="grid gap-3">
          <div className="grid grid-cols-3 gap-2">
            <dt className="text-muted-foreground">Last Seen</dt>
            <dd className="col-span-2">{entity.last_seen}</dd>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <dt className="text-muted-foreground">Last Location</dt>
            <dd className="col-span-2">{entity.last_location}</dd>
          </div>
        </dl>
      </div>

      <div className="space-y-3">
        <h3 className="text-lg font-medium">Activity Timeline</h3>
        <Timeline activities={activities} />
      </div>
    </div>
  )
}
