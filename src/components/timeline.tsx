type Activity = {
  event_id:string,
  event_type:string,
  location:string,
  timestamp:string,
}

export function Timeline({ activities }: { activities: Activity[] }) {
  console.log(activities)
  if (!activities?.length) {
    return (
      <div className="text-sm text-muted-foreground">
        No activity recorded for this entity.
      </div>
    )
  }

  return (
    <ol className="relative border-s pl-6 space-y-6">
      {activities.map((a, idx) => {
        const at = new Date(a.timestamp)
        const dateLabel = isNaN(at.getTime())
          ? a.timestamp
          : at.toLocaleString(undefined, {
              dateStyle: "medium",
              timeStyle: "short",
            })

        return (
          <li
            key={a.event_id?? idx}
            className="ms-6 transition hover:bg-muted/30 rounded-lg p-2"
          >
            {/* Timeline dot */}
            <span
              className="absolute -start-1.5 mt-2 size-3 rounded-full border bg-primary/80"
              aria-hidden
            />

            {/* Event details */}
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <h4 className="font-medium text-pretty capitalize">
                  {a.event_id || "Unknown Event"}
                </h4>
                <time className="text-xs text-muted-foreground whitespace-nowrap">
                  {dateLabel}
                </time>
              </div>

              <p className="text-sm leading-relaxed text-muted-foreground">
                {a.event_type
                  ? `Event Type: ${a.event_type}`
                  : "No additional details provided."}
                {a.location ? (
                  <span className="block text-xs mt-0.5 text-foreground">
                    Location: {a.location}
                  </span>
                ) : null}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
