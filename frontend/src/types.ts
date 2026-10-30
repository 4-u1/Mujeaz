/**
 * Mujeaz (مُجاز) - Core TypeScript Definitions
 */

export type Language = 'ar' | 'en';

export type PriorityLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type CaseStatus = 
  | 'DRAFT'
  | 'RISK_DETECTED'
  | 'EVIDENCE_SEARCHING'
  | 'DECISION_READY'
  | 'SUBMITTED'
  | 'APPROVED'
  | 'DENIED'
  | 'RECOVERY_IN_PROGRESS'
  | 'APPEAL_READY'
  | 'RECOVERED';

export interface ClinicalFact {
  id: string;
  fact: string; // e.g. "6 Physiotherapy Sessions Completed"
  factAr: string;
  category: 'DIAGNOSIS' | 'SYMPTOM' | 'CONSERVATIVE_CARE' | 'MEDICATION' | 'LAB' | 'PROCEDURE';
  source: string; // e.g. "Encounter #2081 - Orthopedic Note"
  date: string; // e.g. "2026-06-11"
  confidence: number; // 0-100
}

export interface PolicyRule {
  id: string;
  code: string;
  title: string;
  titleAr: string;
  requirement: string;
  requirementAr: string;
  status: 'PASSED' | 'WARNING' | 'FAILED' | 'PENDING';
  evidenceSource?: string;
}

export interface EvidenceItem {
  id: string;
  requirement: string;
  requirementAr: string;
  status: 'FOUND' | 'MISSING' | 'PARTIAL';
  matchedFact?: string;
  sourceEncounter?: string;
  date?: string;
  confidence: number;
}

export interface DiscoverableEvidence {
  evidenceItems: EvidenceItem[];
  satisfiesRuleIds: string[];     // policy rules that become PASSED once this evidence is attached
  evidenceSource: string;         // e.g. "Encounter #1820 - Physical Therapy"
  readinessAfter: Partial<ReadinessBreakdown>;
  denialRiskAfter: number;        // 0-100
  summary: string;
  summaryAr: string;
}

export interface ReadinessBreakdown {
  clinicalEvidence: number; // 0-100
  policyMatch: number;      // 0-100
  documentation: number;    // 0-100
  codingIntegrity: number;  // 0-100
  requiredAttachments: number; // 0-100
  administrativeCompleteness: number; // 0-100
  overallScore: number;     // 0-100
  readinessLabel: string;   // e.g. "Decision Ready" or "Action Required"
  readinessLabelAr: string;
  warningNotice?: string;
  warningNoticeAr?: string;
}

export interface RevenueRisk {
  financialValue: number;    // SAR
  denialRiskPercentage: number; // 0-100
  revenueAtRisk: number;     // SAR
  recoverableValue: number;  // SAR
  priority: PriorityLevel;
}

export interface AgentRunState {
  agentId: 'A1' | 'A2' | 'A3' | 'A4' | 'A5' | 'A6';
  name: string;
  nameAr: string;
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FLAGGED';
  outputSummary: string;
  outputSummaryAr: string;
  durationMs: number;
  timestamp: string;
}

export interface FHIRPayload {
  resourceType: 'Claim' | 'ClaimResponse';
  id: string;
  status: string;
  patientRef: string;
  providerRef: string;
  payerRef: string;
  diagnosisCodes: { code: string; display: string }[];
  procedureCodes: { code: string; display: string; costSAR: number }[];
  attachmentsCount: number;
  rawJson: string;
}

export interface AppealEvidenceMap {
  denialReason: string;
  denialReasonAr: string;
  rootCause: string;
  rootCauseAr: string;
  missingRequirement: string;
  missingRequirementAr: string;
  foundEvidence: {
    fact: string;
    factAr: string;
    source: string;
    date: string;
  }[];
  appealStrength: number; // 0-100
  appealStrategy: string;
  appealStrategyAr: string;
  formalLetterEn: string;
  formalLetterAr: string;
}

export interface ClaimDigitalTwin {
  id: string; // server UUID
  legacyId?: string | null; // e.g. 'case-4922' for the original demo cases
  dataSource?: 'legacy-demo' | 'synthetic';
  analyzed?: boolean;
  allowedTransitions?: CaseStatus[];
  claimNumber: string;
  patientName: string;
  patientId: string;
  age: number | null;
  gender: string;
  doctorName: string;
  specialty: string;
  facilityName: string;
  payerName: string;
  payerCode: string;
  requestedService: string;
  requestedServiceAr: string;
  cptCode: string;
  icd10Code: string;
  createdDate: string;
  status: CaseStatus;
  
  // Clinical Order
  clinicalNoteText: string;
  
  // Risk & Financials
  revenueRisk: RevenueRisk;
  
  // Score
  readinessScore: ReadinessBreakdown;
  
  // Facts & Rules
  clinicalFacts: ClinicalFact[];
  policyRules: PolicyRule[];
  evidenceItems: EvidenceItem[];
  
  // Agents
  agentRuns: AgentRunState[];
  
  // FHIR
  fhirPayload: FHIRPayload;
  
  // Evidence that exists elsewhere in the patient's record (demo data) and that the
  // Evidence Hunter (A2) can surface. Empty or absent means a deep search finds nothing new.
  discoverableEvidence?: DiscoverableEvidence;

  // Recovery if denied
  appealPackage?: AppealEvidenceMap;
  
  // Audit Trail
  auditTrail: {
    timestamp: string;
    action: string;
    actionAr: string;
    actor: string;
  }[];
}

export interface CommandCenterMetrics {
  revenueProtectedTodaySAR: number;
  revenueAtRiskSAR: number;
  revenueRecoveredSAR: number;
  preventedDenialsCount: number;
  activeAuthorizationsCount: number;
  recoveryQueueCount: number;
  cleanPassRate: number; // %
  averageReadinessScore: number;
  totalCases?: number;
  analyzedCases?: number;
  basis?: string;
}
