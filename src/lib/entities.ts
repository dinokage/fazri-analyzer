const BACKEND_URL = process.env.BACKEND_URL

export async function getTimelineData(id: string, start: string, end: string) {
  const res = await fetch(
    `${BACKEND_URL}/api/v1/graph/timeline/${id}?start_date=${start}&end_date=${end}`,
    { next: { revalidate: 60 } }
  )
  return res.json()
}

export async function getTimelineSummary(id: string, start: string, end: string) {
  const res = await fetch(
    `${BACKEND_URL}/api/v1/graph/timeline/${id}/summary?start_date=${start}&end_date=${end}`,
    { next: { revalidate: 60 } }
  )
  return res.json()
}


export async function getFusionReport(id: string) {
  const res = await fetch(
    `${BACKEND_URL}/api/v1/entities/${id}/fusion-report`,
    { next: { revalidate: 60 } }
  )
  return res.json()
}
export async function getEntityById(entityId: string) {
  const response = await fetch(`${BACKEND_URL}/api/v1/entities/${entityId}`, {
    method: 'GET',
    headers: {
      accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch entity ${entityId}: ${response.status}`);
  }

  return await response.json();
}