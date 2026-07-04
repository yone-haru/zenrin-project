export function formatDistance(meters: number): string {
  return meters >= 1000 ? `${(meters / 1000).toFixed(1)}km` : `${Math.round(meters)}m`
}

export function formatDuration(seconds: number): string {
  return `約${Math.max(1, Math.round(seconds / 60))}分`
}
