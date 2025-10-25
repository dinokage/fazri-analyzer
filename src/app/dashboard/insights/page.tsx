import React from 'react'
import RoundedPieChart from './pie'
import { StrokeMultipleRadarChart } from './radar'

function Page() {
  return (
    <div className="flex flex-col md:flex-row items-stretch gap-6 p-4">
      <div className="flex-1">
        <RoundedPieChart />
      </div>
      <div className="flex-1">
        <StrokeMultipleRadarChart />
      </div>
    </div>
  )
}

export default Page