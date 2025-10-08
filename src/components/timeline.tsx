type Activity = {
  id: string
  entityId: string
  timestamp: string
  title: string
  description: string
  location?: string
}

export function Timeline({ activities }: { activities: Activity[] }) {
  if (!activities?.length) {
    return <div className="text-sm text-muted-foreground">No activity recorded for this entity.</div>
  }

  return (
    <ol className="relative border-s pl-6 space-y-6">
      {activities.map((a, idx) => {
        const at = new Date(a.timestamp)
        const dateLabel = isNaN(at.getTime()) ? a.timestamp : at.toLocaleString()
        return (
          <li key={idx} className="ms-6">
            <span className="absolute -start-1.5 mt-1 size-3 rounded-full border bg-background" aria-hidden />
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-medium text-pretty">{a.title}</h4>
                <time className="text-xs text-muted-foreground whitespace-nowrap">{dateLabel}</time>
              </div>
              <p className="text-sm leading-relaxed">
                {a.description}
                {a.location ? ` — ${a.location}` : ""}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
