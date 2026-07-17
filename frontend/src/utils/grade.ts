/**
 * 危険度ランク（plan v3.3）。
 * バックエンドは引き続き safety_score（0-100）/ safety_grade（A-E）を返すが、
 * フロントの表示は「危険度D = 100 - safety_score」を5段階ランクに変換したものを使う。
 */
export interface DangerRank {
  /** ランクラベル（安全/注意/危険/非常に危険/要改善） */
  label: string
  /** ランク配色 */
  color: string
  /** 危険度D（0-100、100-safety_score をクランプした値） */
  danger: number
}

interface RankRow {
  maxDanger: number
  label: string
  color: string
}

/** 班の要望どおりの5段階しきい値（D 0-20/21-40/41-60/61-80/81-100）。 */
export const RANK_TABLE: readonly RankRow[] = [
  { maxDanger: 20, label: '安全', color: '#1a7f37' },
  { maxDanger: 40, label: '注意', color: '#b58a00' },
  { maxDanger: 60, label: '危険', color: '#d4620e' },
  { maxDanger: 80, label: '非常に危険', color: '#c62828' },
  { maxDanger: 100, label: '要改善', color: '#202124' },
]

/** safety_score(0-100) から危険度ランク（D・ラベル・色）を導出する。 */
export function rankForSafetyScore(safetyScore: number): DangerRank {
  const danger = Math.min(100, Math.max(0, Math.round(100 - safetyScore)))
  const row = RANK_TABLE.find((entry) => danger <= entry.maxDanger) ?? RANK_TABLE[RANK_TABLE.length - 1]
  return { label: row.label, color: row.color, danger }
}
