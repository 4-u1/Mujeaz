import { describe, expect, it } from 'vitest';
import vectors from '../../shared/scoring_vectors.json';
import {
  computeOverall,
  computeRevenueRisk,
  denialRisk,
  evidenceScore,
  readinessLabel,
  ruleScore,
  type EvidenceStatus,
  type RuleStatus,
} from '../../shared/scoring';

describe('shared scoring vectors (TypeScript reference)', () => {
  it('has at least 200 vectors', () => {
    expect(vectors.vectors.length).toBeGreaterThanOrEqual(200);
  });

  it('reproduces every vector', () => {
    for (const v of vectors.vectors) {
      const rules = v.input.rules as RuleStatus[];
      const evidence = v.input.evidence as EvidenceStatus[];
      const overall = computeOverall(v.input.components, { hasFailedRule: rules.includes('FAILED') });
      const risk = denialRisk(overall.overallScore, rules);
      expect(ruleScore(rules)).toBe(v.output.ruleScore);
      expect(evidenceScore(evidence)).toBe(v.output.evidenceScore);
      expect(overall).toEqual(v.output.overall);
      expect(readinessLabel(overall.overallScore).en).toBe(v.output.label);
      expect(risk).toBe(v.output.denialRisk);
      expect(computeRevenueRisk(v.input.financialValue, risk, evidence)).toEqual(v.output.revenueRisk);
    }
  });
});
