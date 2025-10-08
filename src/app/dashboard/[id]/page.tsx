"use client"

import { useEffect, useState } from "react"
import { notFound } from "next/navigation"
import {
  getEntityById,
  getTimelineData,
  getTimelineSummary,
  getFusionReport,
} from "@/lib/entities"
import { Timeline } from "@/components/timeline"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"

export default function EntityDetailsPage({
  params,
}: {
  params: { id: string }
}) {
  const [entity, setEntity] = useState<any>(null)
  const [timelineData, setTimelineData] = useState<any>(null)
  const [summaryData, setSummaryData] = useState<any>(null)
  const [fusionData, setFusionData] = useState<any>(null)
  const [duration, setDuration] = useState("12h")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function fetchEntityAndFusion() {
      const entityData = await getEntityById(params.id)
      if (!entityData || !entityData.entity) return notFound()
      setEntity(entityData.entity)

      const fusion = await getFusionReport(params.id)
      setFusionData(fusion)
    }

    fetchEntityAndFusion()
  }, [params.id])

  useEffect(() => {
    if (!entity) return

    const now = new Date()
    let start = new Date()

    switch (duration) {
      case "12h":
        start.setHours(now.getHours() - 12)
        break
      case "24h":
        start.setHours(now.getHours() - 24)
        break
      case "48h":
        start.setHours(now.getHours() - 48)
        break
      case "7d":
        start.setDate(now.getDate() - 7)
        break
    }

    async function fetchTimelineAndSummary() {
      setLoading(true)
      const [timeline, summary] = await Promise.all([
        getTimelineData(params.id, start.toISOString(), now.toISOString()),
        getTimelineSummary(params.id, start.toISOString(), now.toISOString()),
      ])
      setTimelineData(timeline)
      setSummaryData(summary)
      setLoading(false)
    }

    fetchTimelineAndSummary()
  }, [duration, entity, params.id])

  if (!entity) return <div>Loading entity details...</div>

  return (
    <div className="space-y-8">
      {/* Entity Header */}
      <div className="flex items-start gap-4">
        <Avatar className="size-16 md:size-20">
          <AvatarImage
            src={`/placeholder.svg?height=96&width=96&query=profile%20photo%20portrait`}
            alt={`${entity.name} profile photo`}
          />
          <AvatarFallback>{entity.name ? entity.name[0] : "?"}</AvatarFallback>
        </Avatar>

        <div className="min-w-0">
          <h2 className="text-2xl font-semibold text-pretty">
            {entity.name}
            <span className="ml-2 align-middle rounded-full border px-2 py-0.5 text-sm">
              {entity.entity_type}
            </span>
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            {entity.email ?? "No email provided"}
          </p>
        </div>
      </div>

      {/* Entity Details */}
      <div className="grid gap-6 md:grid-cols-2">
        <dl className="grid gap-3">
          <Detail label="Entity ID" value={entity.entity_id} />
          <Detail
            label="Student ID"
            value={
              entity.all_identifiers?.student_id?.[0] ??
              getIdentifierValue(entity, "student_id")
            }
          />
          <Detail label="Department" value={entity.department} />
        </dl>

        <dl className="grid gap-3">
          <Detail label="Card ID" value={getIdentifierValue(entity, "card_id")} />
          <Detail label="Device Hash" value={getIdentifierValue(entity, "device_hash")} />
          <Detail label="Face ID" value={getIdentifierValue(entity, "face_id")} />
        </dl>
      </div>

      {/* Duration Selector */}
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium">Time Range:</label>
        <Select value={duration} onValueChange={setDuration}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="12h">Last 12 hours</SelectItem>
            <SelectItem value="24h">Last 24 hours</SelectItem>
            <SelectItem value="48h">Last 48 hours</SelectItem>
            <SelectItem value="7d">Last 7 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Fusion Report */}
      {fusionData && (
        <Card>
          <CardHeader>
            <CardTitle>Fusion Report</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p>
              <strong>Overall Confidence:</strong>{" "}
              {fusionData?.overall_confidence ?? "N/A"}
            </p>
            <ul className="space-y-2">
              {fusionData?.identifiers_by_source?.profiles?.map((id: any) => (
                <li
                  key={id.value}
                  className="grid grid-cols-5 text-sm border-b py-2"
                >
                  <span className="font-medium capitalize">{id.type}</span>
                  <span className="col-span-2">{id.value}</span>
                  <span>{id.confidence}</span>
                  <span className="text-muted-foreground">
                    {new Date(id.first_seen).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      {summaryData && (
        <Card>
          <CardHeader>
            <CardTitle>Activity Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed mb-4">
              {summaryData?.summary ?? "No summary available"}
            </p>

            <div className="grid md:grid-cols-2 gap-4">
              {Object.entries(summaryData?.detailed_summary || {}).map(
                ([period, info]: any) => (
                  <Card key={period} className="p-3">
                    <p className="font-semibold capitalize">{period}</p>
                    <p className="text-sm">{info.description}</p>
                  </Card>
                )
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timeline */}
      {timelineData && (
        <div className="space-y-3">
          <h3 className="text-lg font-medium">Activity Timeline</h3>
          {loading ? (
            <p className="text-muted-foreground text-sm">Loading timeline...</p>
          ) : (
            <Timeline activities={timelineData?.events || []} />
          )}
        </div>
      )}

      {/* Gaps */}
      {timelineData && (
        <Card>
          <CardHeader>
            <CardTitle>Detected Gaps</CardTitle>
          </CardHeader>
          <CardContent>
            {timelineData?.gaps?.length ? (
              <ul className="space-y-3">
                {timelineData.gaps.map((gap: any, i: number) => (
                  <li key={i} className="border-b pb-2 text-sm">
                    <p>
                      <strong>Duration:</strong> {gap.duration_hours.toFixed(2)} hrs
                    </p>
                    <p>
                      <strong>From:</strong>{" "}
                      {new Date(gap.start_time).toLocaleString()} →{" "}
                      <strong>To:</strong>{" "}
                      {new Date(gap.end_time).toLocaleString()}
                    </p>
                    <p>
                      <strong>Last:</strong> {gap.last_location} (
                      {gap.last_event_type}) → <strong>Next:</strong>{" "}
                      {gap.next_location} ({gap.next_event_type})
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No inactivity gaps detected.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function Detail({ label, value }: { label: string; value: any }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="col-span-2">{value ?? "N/A"}</dd>
    </div>
  )
}

function getIdentifierValue(entity: any, type: string) {
  const identifier = entity.identifiers?.find((id: any) => id.type === type)
  return identifier ? identifier.value : "N/A"
}
