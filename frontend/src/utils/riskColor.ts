export function colorForRiskScore(riskScore: number | null): string {
  if (riskScore === null) return '#9ca3af'
  if (riskScore <= 2) return '#22c55e'
  if (riskScore === 3) return '#eab308'
  if (riskScore === 4) return '#f97316'
  return '#ef4444'
}
