/**
 * Generates shared/scoring_vectors.json from the TypeScript scoring reference.
 * Both the frontend (Vitest) and the backend (pytest) must reproduce every vector.
 *
 *   node --experimental-strip-types shared/generate-scoring-vectors.ts
 */
import { writeFileSync } from 'node:fs';
import {
  computeOverall,
  computeRevenueRisk,
  denialRisk,
  evidenceScore,
  readinessLabel,
  ruleScore,
  type EvidenceStatus,
  type ReadinessComponents,
  type RuleStatus,
} from './scoring.ts';

// Deterministic PRNG (mulberry32) so the file is reproducible.
function rng(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const r = rng(20261030);
const pick = <T,>(xs: readonly T[]) => xs[Math.floor(r() * xs.length)];
const EDGE = [0, 49.5, 50, 50.5, 59.5, 60, 60.5, 69.4, 69.5, 70, 89.5, 90, 99.5, 100];
const num = () => (r() < 0.25 ? pick(EDGE) : r() < 0.5 ? Math.round(r() * 1000) / 10 : Math.floor(r() * 101));
const RULES: RuleStatus[] = ['PASSED', 'WARNING', 'FAILED'];
const EVID: EvidenceStatus[] = ['FOUND', 'PARTIAL', 'MISSING'];

const vectors = [];
for (let i = 0; i < 250; i++) {
  const components: ReadinessComponents = {
    clinicalEvidence: num(),
    policyMatch: num(),
    documentation: num(),
    codingIntegrity: r() < 0.15 ? pick([40, 69, 69.5, 70]) : num(),
    requiredAttachments: num(),
    administrativeCompleteness: num(),
  };
  const rules = Array.from({ length: Math.floor(r() * 5) }, () => pick(RULES));
  const evidence = Array.from({ length: Math.floor(r() * 5) }, () => pick(EVID));
  const financialValue = pick([0, 2800, 1900, 68000, 144000, Math.round(r() * 50000 * 100) / 100]);
  const overall = computeOverall(components, { hasFailedRule: rules.includes('FAILED') });
  const risk = denialRisk(overall.overallScore, rules);
  vectors.push({
    input: { components, rules, evidence, financialValue },
    output: {
      ruleScore: ruleScore(rules),
      evidenceScore: evidenceScore(evidence),
      overall,
      label: readinessLabel(overall.overallScore).en,
      denialRisk: risk,
      revenueRisk: computeRevenueRisk(financialValue, risk, evidence),
    },
  });
}

writeFileSync(
  new URL('./scoring_vectors.json', import.meta.url),
  JSON.stringify({ generator: 'shared/generate-scoring-vectors.ts', count: vectors.length, vectors }, null, 1) + '\n',
);
console.log(`wrote ${vectors.length} vectors`);
