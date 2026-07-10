import type { SafetyGrade } from '../api/route'

/** 契約v3で固定の安全グレード配色（A=緑〜E=赤）。 */
export const GRADE_COLOR: Record<SafetyGrade, string> = {
  A: '#1a7f37',
  B: '#4d9e2f',
  C: '#b58a00',
  D: '#d4620e',
  E: '#c62828',
}
