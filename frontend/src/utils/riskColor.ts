/** 投稿(Report)マーカー用の配色。null(未算出)を含む4段階+グレー。 */
export function colorForRiskScore(riskScore: number | null): string {
  if (riskScore === null) return '#9ca3af'
  if (riskScore <= 2) return '#22c55e'
  if (riskScore === 3) return '#eab308'
  if (riskScore === 4) return '#f97316'
  return '#ef4444'
}

/** 危険度スコア(hazard_points / danger_reports)の主色。デザイントークンの赤/橙/黄。 */
export function riskColor(score: number | null): string {
  if (score === null) return '#94a3b8'
  if (score >= 4) return '#ef4444'
  if (score === 3) return '#f97316'
  return '#eab308'
}

/** 危険度スコアの淡色背景。 */
export function riskSoftColor(score: number | null): string {
  if (score === null) return '#f1f5f9'
  if (score >= 4) return '#fee2e2'
  if (score === 3) return '#ffedd5'
  return '#fef3c7'
}

/** 危険度カラー上で読みやすい文字色。 */
export function readableRiskText(score: number | null): string {
  if (score === null) return '#334155'
  return score <= 2 ? '#422006' : '#ffffff'
}
