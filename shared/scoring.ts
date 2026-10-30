/**
 * Mujeaz deterministic scoring (PRD §8).
 *
 * The LLM extracts facts and evaluates rules; the numbers shown to users
 * (Readiness Score, Revenue at Risk, Recoverable Value) are computed here so
 * they are reproducible and explainable.
 */

export type RuleStatus = 'PASSED' | 'WARNING' | 'FAILED';
export type EvidenceStatus = 'FOUND' | 'PARTIAL' | 'MISSING';
export type Priority = 'HIGH' | 'MEDIUM' | 'LOW';

export interface ReadinessComponents {
  clinicalEvidence: number;
  policyMatch: number;
  documentation: number;
  codingIntegrity: number;
  requiredAttachments: number;
  administrativeCompleteness: number;
}

export const READINESS_WEIGHTS: Record<keyof ReadinessComponents, number> = {
  clinicalEvidence: 0.3,
  policyMatch: 0.25,
  documentation: 0.15,
  codingIntegrity: 0.15,
  requiredAttachments: 0.1,
  administrativeCompleteness: 0.05,
};

/** Hard gates: a failed mandatory rule caps the score at 60; invalid coding caps it at 50. */
export const GATE_FAILED_RULE_CAP = 60;
export const GATE_INVALID_CODING_CAP = 50;
export const INVALID_CODING_THRESHOLD = 70;

const clamp = (n: number, min: number, max: number) => Math.min(max, Math.max(min, n));
const safe = (n: unknown) => (typeof n === 'number' && Number.isFinite(n) ? clamp(n, 0, 100) : 0);

/** Share of rules passed (WARNING counts half). Returns null when there are no rules. */
export function ruleScore(statuses: RuleStatus[]): number | null {
  if (statuses.length === 0) return null;
  const pts = statuses.reduce((sum, s) => sum + (s === 'PASSED' ? 1 : s === 'WARNING' ? 0.5 : 0), 0);
  return Math.round((pts / statuses.length) * 100);
}

/** Share of evidence requirements found (PARTIAL counts half). Returns null when there are none. */
export function evidenceScore(statuses: EvidenceStatus[]): number | null {
  if (statuses.length === 0) return null;
  const pts = statuses.reduce((sum, s) => sum + (s === 'FOUND' ? 1 : s === 'PARTIAL' ? 0.5 : 0), 0);
  return Math.round((pts / statuses.length) * 100);
}

export function readinessLabel(score: number): { en: string; ar: string } {
  if (score >= 90) return { en: 'Decision Ready', ar: 'جاهز للقرار' };
  if (score >= 70) return { en: 'Action Recommended', ar: 'يُنصح بإجراء قبل الإرسال' };
  return { en: 'Action Required', ar: 'يتطلب إجراء قبل الإرسال' };
}

export function computeOverall(
  c: ReadinessComponents,
  gates: { hasFailedRule: boolean },
): { overallScore: number; gateApplied: string | null } {
  let score = 0;
  (Object.keys(READINESS_WEIGHTS) as (keyof ReadinessComponents)[]).forEach((k) => {
    score += safe(c[k]) * READINESS_WEIGHTS[k];
  });
  score = Math.round(score);
  let gateApplied: string | null = null;
  if (safe(c.codingIntegrity) < INVALID_CODING_THRESHOLD && score > GATE_INVALID_CODING_CAP) {
    score = GATE_INVALID_CODING_CAP;
    gateApplied = 'INVALID_CODING';
  } else if (gates.hasFailedRule && score > GATE_FAILED_RULE_CAP) {
    score = GATE_FAILED_RULE_CAP;
    gateApplied = 'FAILED_MANDATORY_RULE';
  }
  return { overallScore: score, gateApplied };
}

/**
 * Pre-submission denial-risk heuristic (MVP, rule-based — to be replaced by a
 * trained model once real outcome data exists).
 */
export function denialRisk(overallScore: number, rules: RuleStatus[]): number {
  let p = 100 - overallScore;
  if (rules.includes('FAILED')) p = Math.max(p, 85);
  else if (rules.includes('WARNING')) p = Math.max(p, 50);
  return clamp(Math.round(p), 2, 98);
}

export function computeRevenueRisk(
  financialValue: number,
  denialRiskPercentage: number,
  evidence: EvidenceStatus[],
): {
  financialValue: number;
  denialRiskPercentage: number;
  revenueAtRisk: number;
  recoverableValue: number;
  priority: Priority;
} {
  const value = Math.max(0, Math.round(financialValue || 0));
  const p = clamp(denialRiskPercentage, 0, 100);
  const revenueAtRisk = Math.round(value * (p / 100));
  const support = (evidenceScore(evidence) ?? 0) / 100;
  const recoverableValue = Math.round(revenueAtRisk * support);
  const priority: Priority = p >= 60 || revenueAtRisk >= 10000 ? 'HIGH' : p >= 30 ? 'MEDIUM' : 'LOW';
  return { financialValue: value, denialRiskPercentage: p, revenueAtRisk, recoverableValue, priority };
}
