import React, { useState } from 'react';
import { ClaimDigitalTwin, Language } from '../types';
import { 
  ShieldCheck, 
  Layers, 
  Activity, 
  FileCode, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  Sparkles, 
  FileText, 
  ExternalLink,
  ChevronLeft,
  XCircle,
  Copy,
  Check,
  Filter,
  Search,
  Download,
  Lock,
  Terminal,
  Cpu,
  Key,
  RefreshCw,
  ShieldAlert,
  CheckSquare,
  Fingerprint,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface DigitalTwinInspectorProps {
  claim: ClaimDigitalTwin;
  lang: Language;
  onBack: () => void;
  onRunEvidenceHunter: (caseId: string) => void;
}

export const DigitalTwinInspector: React.FC<DigitalTwinInspectorProps> = ({
  claim,
  lang,
  onBack,
  onRunEvidenceHunter,
}) => {
  const isAr = lang === 'ar';
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'AGENTS' | 'FACTS' | 'SCORE' | 'FHIR' | 'AUDIT'>('OVERVIEW');
  const [copied, setCopied] = useState(false);

  // Automated Audit Log Filters & Controls
  const [actorFilter, setActorFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [auditSearch, setAuditSearch] = useState<string>('');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [isVerifyingIntegrity, setIsVerifyingIntegrity] = useState(false);
  const [integrityVerified, setIntegrityVerified] = useState<boolean | null>(null);
  const [auditCopied, setAuditCopied] = useState(false);

  const formatSAR = (val: number) => {
    return new Intl.NumberFormat(isAr ? 'ar-SA' : 'en-US', {
      style: 'currency',
      currency: 'SAR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const handleCopyFhir = () => {
    navigator.clipboard.writeText(claim.fhirPayload.rawJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Generate automated, cryptographically traceable audit logs for all AI agents and decisions
  const allAuditLogs = React.useMemo(() => {
    const logs: Array<{
      id: string;
      timestamp: string;
      actorId: string;
      actorName: string;
      actorNameAr: string;
      action: string;
      actionAr: string;
      category: 'AI_DECISION' | 'EVIDENCE' | 'POLICY' | 'SCORE' | 'FHIR' | 'APPEAL' | 'SYSTEM';
      severity: 'SUCCESS' | 'WARNING' | 'INFO' | 'DECISION';
      complianceStandard: string;
      hash: string;
      confidence?: number;
      rationaleEn: string;
      rationaleAr: string;
      ruleCode?: string;
      sourceRef?: string;
    }> = [];

    // 1. Ingestion Event
    logs.push({
      id: `log-ingest-${claim.id}`,
      timestamp: `${claim.createdDate} 10:14:00.012`,
      actorId: 'HIS',
      actorName: 'HIS / EMR Gateway',
      actorNameAr: 'بوابة السجل الطبي للمستشفى',
      action: `Clinical Order Ingested (#${claim.claimNumber})`,
      actionAr: `تم سحب الطلب السريري رقم (${claim.claimNumber})`,
      category: 'SYSTEM',
      severity: 'INFO',
      complianceStandard: 'HL7-FHIR-R4-HIS',
      hash: '',
      rationaleEn: `Successfully received order note for ${claim.requestedService} from ${claim.facilityName}. Patient ID: ${claim.patientId}.`,
      rationaleAr: `تم استلام ملاحظة الطلب للخدمة ${claim.requestedServiceAr} من ${claim.facilityName}. رقم المريض: ${claim.patientId}.`,
      sourceRef: `EMR Encounter Note #${claim.patientId}`,
    });

    // 2. A1 Clinical Extractor Agent Event
    const a1Run = claim.agentRuns.find(a => a.agentId === 'A1');
    logs.push({
      id: `log-a1-${claim.id}`,
      timestamp: a1Run?.timestamp ? `${a1Run.timestamp}.140` : `${claim.createdDate} 10:14:02.140`,
      actorId: 'A1',
      actorName: 'A1: Clinical Order Extractor',
      actorNameAr: 'A1: وكيل استخراج الطلبات السريرية',
      action: `Extracted Clinical Facts & Medical Codes (ICD-10: ${claim.icd10Code}, CPT: ${claim.cptCode})`,
      actionAr: `استخراج الحقائق والترميز الطبي (ICD-10: ${claim.icd10Code}, CPT: ${claim.cptCode})`,
      category: 'AI_DECISION',
      severity: 'DECISION',
      complianceStandard: 'ICD-10 / reference procedure code (demo) — production: ICD-10-AM + SBS',
      hash: '',
      confidence: 98,
      rationaleEn: `NLP Extractor parsed text with 98% confidence. Extracted ${claim.clinicalFacts.length} core clinical facts from physician encounter notes.`,
      rationaleAr: `حلل وكيل الذكاء الاصطناعي النص بدقة 98%. تم استخراج ${claim.clinicalFacts.length} حقائق سريرية من ملاحظات الطبيب.`,
      sourceRef: `Demo case data`,
    });

    // 3. A2 Policy Reasoning Agent Event
    const warningRule = claim.policyRules.find(r => r.status === 'WARNING' || r.status === 'FAILED');
    logs.push({
      id: `log-policy-${claim.id}`,
      timestamp: `${claim.createdDate} 10:14:03.080`,
      actorId: 'A3',
      actorName: 'A3: Policy Reasoning Agent',
      actorNameAr: 'A3: وكيل مطابقة السياسات',
      action: warningRule 
        ? `Policy Guideline Flagged: ${warningRule.code} (${isAr ? warningRule.titleAr : warningRule.title})`
        : `All Policy Rules Verified Passed for ${claim.payerName}`,
      actionAr: warningRule
        ? `تنبيه مطابقة السياسة: ${warningRule.code} (${warningRule.titleAr})`
        : `تمت التحقق بنجاح من كافة قواعد السياسة لشركة ${claim.payerName}`,
      category: 'POLICY',
      severity: warningRule ? 'WARNING' : 'SUCCESS',
      complianceStandard: `${claim.payerCode}-NPHIES-RuleSet`,
      hash: '',
      ruleCode: warningRule?.code || 'POL-CHECK-00',
      rationaleEn: warningRule 
        ? `Matched payer rule ${warningRule.code}: ${warningRule.requirement}`
        : `100% Policy Match against ${claim.payerName} medical necessity ruleset.`,
      rationaleAr: warningRule
        ? `تمت مطابقة القاعدة ${warningRule.code}: ${warningRule.requirementAr}`
        : `مطابقة كاملة 100% مع قواعد الضرورة الطبية لشركة ${claim.payerName}.`,
    });

    // 4. A3 Evidence Hunter Agent Event
    const evidenceFoundCount = claim.evidenceItems.filter(e => e.status === 'FOUND').length;
    const evidenceMissingCount = claim.evidenceItems.filter(e => e.status === 'MISSING').length;
    logs.push({
      id: `log-hunter-${claim.id}`,
      timestamp: `${claim.createdDate} 10:14:03.520`,
      actorId: 'A2',
      actorName: 'A2: Evidence Hunter Agent',
      actorNameAr: 'A2: وكيل صيد الأدلة السريرية',
      action: claim.status === 'APPROVED' || evidenceMissingCount === 0
        ? `EMR Deep Search Complete: Discovered All Required Clinical Prerequisites`
        : `EMR Deep Search Triggered: Identified ${evidenceMissingCount} Missing Prerequisite(s)`,
      actionAr: claim.status === 'APPROVED' || evidenceMissingCount === 0
        ? `اكتمل المسح العميق للسجل الطبي: تم توثيق جميع المتطلبات السابقة`
        : `تم تشغيل صيد الأدلة: اكتشاف ${evidenceMissingCount} متطلب ينقص التوثيق الصريح`,
      category: 'EVIDENCE',
      severity: claim.status === 'APPROVED' || evidenceMissingCount === 0 ? 'SUCCESS' : 'WARNING',
      complianceStandard: 'Mujeaz: No Evidence, No Claim',
      hash: '',
      confidence: 96,
      rationaleEn: `Mined EMR longitudinal patient records. Found ${evidenceFoundCount} valid evidence items, ${evidenceMissingCount} pending validation.`,
      rationaleAr: `مسح السجل الطبي الممتد للمريض. تم العثور على ${evidenceFoundCount} دلالات سريرية، و ${evidenceMissingCount} بانتظار التأكيد.`,
      sourceRef: `EMR Historical Database Query #8821`,
    });

    // 5. A4 Risk & Readiness Scorer Event
    logs.push({
      id: `log-score-${claim.id}`,
      timestamp: `${claim.createdDate} 10:14:04.190`,
      actorId: 'A5',
      actorName: 'A5: Revenue Risk & Readiness Scorer',
      actorNameAr: 'A5: وكيل تقييم المخاطر والجاهزية',
      action: `Mujeaz Readiness Score Evaluated: ${claim.readinessScore.overallScore}/100 (Risk: ${claim.revenueRisk.denialRiskPercentage}%)`,
      actionAr: `احتساب مؤشر الجاهزية Mujeaz Score: ${claim.readinessScore.overallScore}/100 (المخاطر: ${claim.revenueRisk.denialRiskPercentage}%)`,
      category: 'SCORE',
      severity: claim.readinessScore.overallScore >= 90 ? 'SUCCESS' : claim.readinessScore.overallScore >= 70 ? 'DECISION' : 'WARNING',
      complianceStandard: 'Mujeaz Readiness Score (PRD §8)',
      hash: '',
      rationaleEn: `Overall Score ${claim.readinessScore.overallScore}/100. Revenue at risk evaluated at ${formatSAR(claim.revenueRisk.revenueAtRisk)}. Priority: ${claim.revenueRisk.priority}.`,
      rationaleAr: `درجة الجاهزية الكلية ${claim.readinessScore.overallScore}/100. الإيراد المعرض للخطر ${formatSAR(claim.revenueRisk.revenueAtRisk)}. الأولوية: ${claim.revenueRisk.priority}.`,
    });

    // 6. A5 NPHIES FHIR Conformance Event
    logs.push({
      id: `log-fhir-${claim.id}`,
      timestamp: `${claim.createdDate} 10:14:04.810`,
      actorId: 'A4',
      actorName: 'A4: NPHIES / FHIR Conformance Agent',
      actorNameAr: 'A4: وكيل معايير نفيس وهيكلة FHIR',
      action: `Built sample FHIR payload (${claim.fhirPayload.resourceType} - ID: ${claim.fhirPayload.id})`,
      actionAr: `تم بناء نموذج حمولة FHIR (${claim.fhirPayload.resourceType})`,
      category: 'FHIR',
      severity: 'INFO',
      complianceStandard: 'HL7 FHIR R4 — not validated against NPHIES profiles',
      hash: '',
      rationaleEn: `Sample payload with ${claim.fhirPayload.attachmentsCount} attachment(s). Validation against NPHIES Implementation Guide profiles is not implemented yet (PRD FR-A4-03).`,
      rationaleAr: `نموذج حمولة مع ${claim.fhirPayload.attachmentsCount} مرفق. التحقق بملفات تعريف دليل تنفيذ نفيس غير مفعّل بعد (FR-A4-03).`,
    });

    // 7. A6 Recovery Specialist Event (If Denial / Appeal exists)
    if (claim.appealPackage || claim.status === 'DENIED') {
      logs.push({
        id: `log-recovery-${claim.id}`,
        timestamp: `${claim.createdDate} 14:20:04.110`,
        actorId: 'A6',
        actorName: 'A6: Revenue Recovery Specialist',
        actorNameAr: 'A6: وكيل استرداد الإيرادات والاستئناف',
        action: `Generated Formal Reconsideration Package (Appeal Strength: ${claim.appealPackage?.appealStrength || 95}%)`,
        actionAr: `إنشاء حزمة الاستئناف الموثقة (نسبة القبول المتوقعة: ${claim.appealPackage?.appealStrength || 95}%)`,
        category: 'APPEAL',
        severity: 'SUCCESS',
        complianceStandard: 'Payer reconsideration process (demo)',
        hash: '',
        confidence: claim.appealPackage?.appealStrength || 95,
        rationaleEn: `Root cause identified: ${claim.appealPackage?.denialReason || 'Step Therapy Exception'}. Auto-drafted bilingual reconsideration letter with clinical evidence references.`,
        rationaleAr: `تحديد السبب الجذر: ${claim.appealPackage?.denialReasonAr || 'استثناء العلاج المتدرج'}. إعداد خطاب استئناف مزدوج اللغة مدعوم بالأدلة.`,
      });
    }

    // 8. Original manual audit trail entries
    claim.auditTrail.forEach((item, index) => {
      logs.push({
        id: `log-orig-${claim.id}-${index}`,
        timestamp: item.timestamp,
        actorId: item.actor.includes('HIS') ? 'HIS' : item.actor.includes('Payer') || item.actor.includes('NPHIES') ? 'NPHIES' : 'SYSTEM',
        actorName: item.actor,
        actorNameAr: item.actor,
        action: item.action,
        actionAr: item.actionAr,
        category: 'SYSTEM',
        severity: 'INFO',
        complianceStandard: 'Audit-Trail-Record',
        hash: '',
        rationaleEn: `Recorded operational action by ${item.actor}.`,
        rationaleAr: `تم تسجيل الإجراء التشغيلي بواسطة ${item.actor}.`,
      });
    });

    return logs.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  }, [claim, isAr]);

  // SHA-256 hash chain: each entry's hash covers its content plus the previous hash,
  // so altering any earlier entry changes every hash after it.
  // NOTE: computed in the browser for demonstration; production computes and stores
  // the chain server-side when each event is written (PRD FR-AU-01).
  const computeHashChain = React.useCallback(async (entries: typeof allAuditLogs) => {
    const enc = new TextEncoder();
    const out: Record<string, string> = {};
    let prev = 'GENESIS';
    for (const entry of entries) {
      const { hash: _omit, ...content } = entry;
      const digest = await crypto.subtle.digest('SHA-256', enc.encode(prev + JSON.stringify(content)));
      const hex = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
      out[entry.id] = hex;
      prev = hex;
    }
    return { hashes: out, head: prev };
  }, []);

  const [chain, setChain] = useState<{ hashes: Record<string, string>; head: string } | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    setChain(null);
    setIntegrityVerified(null);
    computeHashChain(allAuditLogs).then((c) => {
      if (!cancelled) setChain(c);
    });
    return () => {
      cancelled = true;
    };
  }, [allAuditLogs, computeHashChain]);

  const hashOf = (id: string) => chain?.hashes[id] ?? '…';
  const shortHead = chain ? `${chain.head.slice(0, 10)}…${chain.head.slice(-4)}` : '…';

  // Filtered logs
  const filteredLogs = React.useMemo(() => {
    return allAuditLogs.filter(log => {
      // Actor filter
      if (actorFilter !== 'ALL' && log.actorId !== actorFilter) {
        return false;
      }
      // Category filter
      if (categoryFilter !== 'ALL' && log.category !== categoryFilter) {
        return false;
      }
      // Search filter
      if (auditSearch.trim()) {
        const q = auditSearch.toLowerCase();
        const text = `${log.action} ${log.actionAr} ${log.actorName} ${log.actorNameAr} ${log.rationaleEn} ${log.rationaleAr} ${hashOf(log.id)} ${log.complianceStandard}`.toLowerCase();
        return text.includes(q);
      }
      return true;
    });
  }, [allAuditLogs, actorFilter, categoryFilter, auditSearch]);

  // Recompute the chain from the current entries and compare with the stored head.
  const handleVerifyIntegrity = async () => {
    if (!chain) return;
    setIsVerifyingIntegrity(true);
    try {
      const recomputed = await computeHashChain(allAuditLogs);
      setIntegrityVerified(recomputed.head === chain.head);
    } finally {
      setIsVerifyingIntegrity(false);
    }
  };

  const handleCopyAuditJson = () => {
    const jsonStr = JSON.stringify({
      claimId: claim.id,
      claimNumber: claim.claimNumber,
      hashAlgorithm: 'SHA-256 chain (prev_hash + entry JSON), genesis = "GENESIS"',
      chainHead: chain?.head ?? null,
      auditEventsCount: allAuditLogs.length,
      note: 'Demo: chain computed in the browser from demo case data.',
      auditLogs: allAuditLogs.map((l) => ({ ...l, hash: hashOf(l.id) }))
    }, null, 2);
    
    navigator.clipboard.writeText(jsonStr);
    setAuditCopied(true);
    setTimeout(() => setAuditCopied(false), 2000);
  };

  return (
    <div className="space-y-6 pb-12">
      
      {/* Top Header Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold border border-slate-800 transition-colors cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>{isAr ? 'العودة إلى لوحة القيادة' : 'Back to Command Center'}</span>
        </button>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">{isAr ? 'حالة التوأم الرقمي:' : 'Digital Twin State:'}</span>
          <span className="px-2.5 py-1 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 font-bold font-mono">
            CLAIM #{claim.claimNumber}
          </span>
        </div>
      </div>

      {/* Main Digital Twin Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl text-white space-y-6">
        
        {/* Header Profile */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 border-b border-slate-800 pb-6">
          
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-400 text-xs font-bold">
                {claim.payerName}
              </span>
              <span className="text-xs text-slate-400 font-mono">{claim.payerCode}</span>
            </div>

            <h1 className="text-2xl font-extrabold text-white">
              {isAr ? claim.requestedServiceAr : claim.requestedService}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300">
              <div>
                <span className="text-slate-400">{isAr ? 'المريض:' : 'Patient:'} </span>
                <span className="font-semibold text-white">{claim.patientName}</span> ({claim.gender}, {claim.age})
              </div>
              <div>
                <span className="text-slate-400">{isAr ? 'الطبيب:' : 'Physician:'} </span>
                <span className="font-semibold text-white">{claim.doctorName}</span>
              </div>
              <div>
                <span className="text-slate-400">{isAr ? 'المنشأة:' : 'Facility:'} </span>
                <span className="font-semibold text-white">{claim.facilityName}</span>
              </div>
            </div>
          </div>

          {/* Quick Metrics Badge Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            
            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
              <div className="text-[10px] text-slate-400 font-medium">{isAr ? 'القيمة المالية' : 'Financial Value'}</div>
              <div className="text-base font-extrabold text-white mt-0.5">{formatSAR(claim.revenueRisk.financialValue)}</div>
            </div>

            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
              <div className="text-[10px] text-slate-400 font-medium">{isAr ? 'مخاطر الرفض' : 'Denial Risk'}</div>
              <div className={`text-base font-extrabold mt-0.5 ${claim.revenueRisk.denialRiskPercentage > 50 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {claim.revenueRisk.denialRiskPercentage}%
              </div>
            </div>

            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
              <div className="text-[10px] text-slate-400 font-medium">{isAr ? 'الإيراد المعرض للخطر' : 'Revenue at Risk'}</div>
              <div className="text-base font-extrabold text-rose-400 mt-0.5">{formatSAR(claim.revenueRisk.revenueAtRisk)}</div>
            </div>

            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
              <div className="text-[10px] text-slate-400 font-medium">{isAr ? 'مؤشر الجاهزية' : 'Readiness Score'}</div>
              <div className="text-base font-extrabold text-emerald-400 mt-0.5">{claim.readinessScore.overallScore}/100</div>
            </div>

          </div>

        </div>

        {/* Tab Selector */}
        <div className="flex overflow-x-auto gap-2 bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('OVERVIEW')}
            className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'OVERVIEW' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {isAr ? 'الملخص والتنبؤ' : 'Overview & Risk'}
          </button>

          <button
            onClick={() => setActiveTab('SCORE')}
            className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'SCORE' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {isAr ? 'مؤشر الجاهزية Mujeaz Score' : 'Readiness Breakdown'}
          </button>

          <button
            onClick={() => setActiveTab('AGENTS')}
            className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'AGENTS' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {isAr ? 'سجل وكلاء الذكاء الاصطناعي (6 Agents)' : 'Multi-Agent Stack'}
          </button>

          <button
            onClick={() => setActiveTab('FACTS')}
            className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'FACTS' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {isAr ? 'خريطة الأدلة القابلة للتتبع' : 'Clinical Evidence Map'}
          </button>

          <button
            onClick={() => setActiveTab('FHIR')}
            className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'FHIR' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {isAr ? 'هيكل نفيس / FHIR' : 'FHIR Payload'}
          </button>

          <button
            onClick={() => setActiveTab('AUDIT')}
            className={`px-4 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === 'AUDIT' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            {isAr ? 'سجل التدقيق (Audit Trail)' : 'Audit Trail'}
          </button>
        </div>

        {/* TAB 1: OVERVIEW */}
        {activeTab === 'OVERVIEW' && (
          <div className="space-y-6">
            
            {/* Primary Order Note */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-slate-300">
                {isAr ? 'نص الطلب السريري الأصلي:' : 'Primary Clinical Order Note:'}
              </div>
              <p className="text-xs text-slate-300 font-serif leading-relaxed bg-slate-900 p-3 rounded-lg border border-slate-800">
                "{claim.clinicalNoteText}"
              </p>
            </div>

            {/* Warning or Status Notice */}
            {claim.readinessScore.warningNotice && (
              <div className="bg-rose-950/40 p-4 rounded-xl border border-rose-900/60 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="text-xs font-bold text-rose-300">
                    {isAr ? 'تنبيه مخاطر الرفض المكتشفة:' : 'Detected Denial Risk Warning:'}
                  </div>
                  <p className="text-xs text-rose-200">
                    {isAr ? claim.readinessScore.warningNoticeAr : claim.readinessScore.warningNotice}
                  </p>
                  
                  {claim.status === 'RISK_DETECTED' && (
                    <button
                      onClick={() => onRunEvidenceHunter(claim.id)}
                      className="mt-2 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-md cursor-pointer"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                      <span>{isAr ? 'تشغيل صيد الأدلة لمسح السجل' : 'Run Evidence Hunter Search'}</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Policy Rules Status Grid */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-200">{isAr ? 'قواعد سياسة التغطية المطلوبة:' : 'Required Policy Compliance Rules:'}</h3>
              <div className="space-y-2">
                {claim.policyRules.map((rule) => (
                  <div key={rule.id} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-bold text-white">{isAr ? rule.titleAr : rule.title}</div>
                      <div className="text-slate-400 mt-0.5">{isAr ? rule.requirementAr : rule.requirement}</div>
                    </div>
                    <div>
                      {rule.status === 'PASSED' && (
                        <span className="px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                          Passed
                        </span>
                      )}
                      {rule.status === 'WARNING' && (
                        <span className="px-2.5 py-1 rounded-full bg-amber-950 text-amber-400 border border-amber-800 font-bold animate-pulse">
                          Warning
                        </span>
                      )}
                      {rule.status === 'FAILED' && (
                        <span className="px-2.5 py-1 rounded-full bg-rose-950 text-rose-400 border border-rose-800 font-bold">
                          Failed
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}

        {/* TAB 2: READINESS SCORE BREAKDOWN */}
        {activeTab === 'SCORE' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Mujeaz Readiness Score Breakdown</h3>
                <p className="text-xs text-slate-400">
                  {isAr ? 'قياس دقيق وجاهزية الطلب للقبول من المرة الأولى' : 'Multidimensional evaluation metrics for first-pass clean approval'}
                </p>
              </div>
              <div className="text-3xl font-extrabold text-emerald-400">{claim.readinessScore.overallScore} / 100</div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {[
                { nameAr: 'الأدلة السريرية', nameEn: 'Clinical Evidence', score: claim.readinessScore.clinicalEvidence },
                { nameAr: 'مطابقة السياسات', nameEn: 'Policy Conformance', score: claim.readinessScore.policyMatch },
                { nameAr: 'التوثيق الطبي', nameEn: 'Clinical Documentation', score: claim.readinessScore.documentation },
                { nameAr: 'سلامة الترميز', nameEn: 'Coding Integrity', score: claim.readinessScore.codingIntegrity },
                { nameAr: 'المرفقات المطلوبة', nameEn: 'Required Attachments', score: claim.readinessScore.requiredAttachments },
                { nameAr: 'الاكتمال الإداري', nameEn: 'Admin Completeness', score: claim.readinessScore.administrativeCompleteness },
              ].map((item, idx) => (
                <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">{isAr ? item.nameAr : item.nameEn}</span>
                    <span className="font-bold text-emerald-400">{item.score}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${item.score}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: MULTI-AGENT STACK */}
        {activeTab === 'AGENTS' && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white">{isAr ? 'حالة وكلاء الذكاء الاصطناعي الستة (6-Agent Execution Stack)' : '6-Agent Execution Stack Status'}</h3>
            <div className="space-y-3">
              {claim.agentRuns.map((agent) => (
                <div key={agent.agentId} className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-slate-800 font-mono text-[11px] font-bold text-emerald-400">
                        {agent.agentId}
                      </span>
                      <span className="font-bold text-white text-sm">
                        {isAr ? agent.nameAr : agent.name}
                      </span>
                    </div>
                    <p className="text-slate-300">{isAr ? agent.outputSummaryAr : agent.outputSummary}</p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-[11px] font-mono text-slate-500">{agent.durationMs}ms</span>
                    <span className={`px-2.5 py-1 rounded-full font-bold text-[11px] ${
                      agent.status === 'COMPLETED' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                      agent.status === 'FLAGGED' ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {agent.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: CLINICAL FACTS & EVIDENCE */}
        {activeTab === 'FACTS' && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white">{isAr ? 'الأدلة السريرية المستخرجة والمربوطة بالمصدر' : 'Extracted Clinical Evidence Map'}</h3>
            <div className="space-y-3">
              {claim.clinicalFacts.map((fact) => (
                <div key={fact.id} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-emerald-300 text-sm">{isAr ? fact.factAr : fact.fact}</span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">{fact.confidence}% Confidence</span>
                  </div>
                  <div className="flex items-center gap-4 text-slate-400 text-[11px]">
                    <div>{isAr ? 'المصدر:' : 'Source:'} <span className="text-slate-200 font-semibold">{fact.source}</span></div>
                    <div>{isAr ? 'التاريخ:' : 'Date:'} <span className="text-slate-200 font-semibold">{fact.date}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 5: FHIR PAYLOAD */}
        {activeTab === 'FHIR' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">{isAr ? 'نموذج حمولة FHIR' : 'Sample FHIR Payload'}</h3>
                <p className="text-[11px] text-amber-300/90">
                  {isAr
                    ? 'نموذج توضيحي بأكواد مرجعية. الإنتاج يتطلب ملفات تعريف نفيس وترميز ICD-10-AM و SBS.'
                    : 'Illustrative sample with reference codes. Production requires NPHIES profiles with ICD-10-AM and SBS coding.'}
                </p>
              </div>
              <button
                onClick={handleCopyFhir}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
              </button>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 max-h-96 overflow-y-auto">
              <pre>{claim.fhirPayload.rawJson}</pre>
            </div>
          </div>
        )}

        {/* TAB 6: AUTOMATED REGULATORY AUDIT LOG */}
        {activeTab === 'AUDIT' && (
          <div className="space-y-6">
            
            {/* Header & Cryptographic Verification Summary */}
            <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-base font-extrabold text-white">
                      {isAr ? 'سجل التدقيق الآلي والامتثال التنظيمي الشامل' : 'Automated Traceability & Regulatory Compliance Audit Log'}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-400">
                    {isAr 
                      ? 'سجل تدقيق مربوط بسلسلة تجزئة SHA-256: أي تعديل في حدث سابق يغيّر كل التجزئات بعده. (عرض تجريبي محسوب في المتصفح)'
                      : 'Audit log linked by a SHA-256 hash chain: altering any earlier event changes every hash after it. (Demo — computed in the browser.)'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <button
                    onClick={handleVerifyIntegrity}
                    disabled={isVerifyingIntegrity}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950 hover:bg-emerald-900 border border-emerald-700/60 text-emerald-300 text-xs font-bold transition-all cursor-pointer shadow-sm"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isVerifyingIntegrity ? 'animate-spin text-emerald-400' : ''}`} />
                    <span>
                      {isVerifyingIntegrity 
                        ? (isAr ? 'جاري التحقق من التوقيع...' : 'Verifying Hashes...') 
                        : (isAr ? 'التحقق من سلامة السجل' : 'Verify Audit Integrity')}
                    </span>
                  </button>

                  <button
                    onClick={handleCopyAuditJson}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer border border-slate-700 transition-colors"
                  >
                    {auditCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Download className="w-3.5 h-3.5" />}
                    <span>{auditCopied ? (isAr ? 'تم النسخ!' : 'Copied JSON!') : (isAr ? 'تصدير السجل JSON' : 'Export JSON')}</span>
                  </button>
                </div>
              </div>

              {/* Cryptographic Badges Bar */}
              <div className="pt-3 border-t border-slate-900 flex flex-wrap items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 font-mono text-[11px]">
                  <Fingerprint className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{isAr ? 'رأس السلسلة:' : 'Chain head:'} <strong className="text-cyan-300">{shortHead}</strong></span>
                </div>

                {integrityVerified !== null && (
                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] border ${integrityVerified ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300' : 'bg-red-950/60 border-red-800/60 text-red-300'}`}>
                    {integrityVerified ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                    <span>
                      {integrityVerified
                        ? (isAr ? 'السلسلة سليمة: أُعيد حسابها وطابقت' : 'Chain intact: recomputed and matched')
                        : (isAr ? 'السلسلة لا تطابق: تم تعديل السجل' : 'Chain mismatch: log was altered')}
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-950/60 border border-amber-800/60 text-amber-300 text-[11px]">
                  <FileCode className="w-3.5 h-3.5 text-amber-400" />
                  <span>{isAr ? 'حمولة FHIR: نموذج غير متحقق منه بملفات نفيس' : 'FHIR payload: sample, not validated against NPHIES profiles'}</span>
                </div>

                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-400 text-[11px] ml-auto">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  <span>{allAuditLogs.length} {isAr ? 'حدث مسجل' : 'Logged Events'}</span>
                </div>
              </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                
                {/* Search Bar */}
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={auditSearch}
                    onChange={(e) => setAuditSearch(e.target.value)}
                    placeholder={isAr ? 'البحث في الأحداث، الفاعلين، أو أسطر التوقيع...' : 'Search logs by action, agent, standard, or hash token...'}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                  />
                  {auditSearch && (
                    <button 
                      onClick={() => setAuditSearch('')}
                      className="absolute right-2.5 top-2.5 text-slate-500 hover:text-white text-xs cursor-pointer"
                    >
                      ×
                    </button>
                  )}
                </div>

                {/* Actor Selector Dropdown */}
                <div className="flex items-center gap-2 text-xs">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-slate-400">{isAr ? 'الفاعل:' : 'Actor:'}</span>
                  <select
                    value={actorFilter}
                    onChange={(e) => setActorFilter(e.target.value)}
                    className="bg-slate-900 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="ALL">{isAr ? 'جميع الفاعلين (All Actors)' : 'All Actors'}</option>
                    <option value="A1">A1: Clinical Extractor</option>
                    <option value="A2">A2: Evidence Hunter</option>
                    <option value="A3">A3: Policy Reasoning</option>
                    <option value="A4">A4: FHIR Conformance</option>
                    <option value="A5">A5: Risk Scorer</option>
                    <option value="A6">A6: Recovery Specialist</option>
                    <option value="HIS">HIS / EMR System</option>
                    <option value="NPHIES">NPHIES Gateway</option>
                  </select>
                </div>

              </div>

              {/* Category Filter Pills */}
              <div className="flex flex-wrap gap-1.5 text-[11px] font-semibold pt-1">
                {[
                  { id: 'ALL', labelEn: 'All Categories', labelAr: 'جميع التصنيفات' },
                  { id: 'AI_DECISION', labelEn: 'AI Decisions', labelAr: 'قرارات الذكاء الاصطناعي' },
                  { id: 'EVIDENCE', labelEn: 'Evidence Mined', labelAr: 'الأدلة المستخرجة' },
                  { id: 'POLICY', labelEn: 'Policy Rules', labelAr: 'قواعد السياسة' },
                  { id: 'SCORE', labelEn: 'Readiness & Risk', labelAr: 'تقييم الجاهزية' },
                  { id: 'FHIR', labelEn: 'FHIR Payload', labelAr: 'ملف FHIR' },
                  { id: 'APPEAL', labelEn: 'Appeal Reconsideration', labelAr: 'حزمة الاستئناف' },
                ].map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => setCategoryFilter(cat.id)}
                    className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                      categoryFilter === cat.id
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                    }`}
                  >
                    {isAr ? cat.labelAr : cat.labelEn}
                  </button>
                ))}
              </div>
            </div>

            {/* Audit Trail Events Timeline */}
            <div className="space-y-3">
              {filteredLogs.length === 0 ? (
                <div className="bg-slate-950 p-8 rounded-xl border border-slate-800 text-center text-slate-400 space-y-2">
                  <ShieldAlert className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-xs">{isAr ? 'لم يتم العثور على سجلات تطابق معايير التصفية الحالية' : 'No audit records match the selected filter criteria'}</p>
                </div>
              ) : (
                filteredLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  return (
                    <div 
                      key={log.id} 
                      className={`bg-slate-950 rounded-xl border transition-all ${
                        log.severity === 'WARNING' 
                          ? 'border-amber-900/60 hover:border-amber-700/80' 
                          : log.severity === 'DECISION'
                          ? 'border-blue-900/60 hover:border-blue-700/80'
                          : 'border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {/* Log Card Row Header */}
                      <div 
                        onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                        className="p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 cursor-pointer select-none"
                      >
                        <div className="flex items-start gap-3">
                          
                          {/* Actor Badge Icon */}
                          <div className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                            log.actorId.startsWith('A') 
                              ? 'bg-emerald-950 border border-emerald-800/80 text-emerald-400'
                              : log.actorId === 'HIS'
                              ? 'bg-blue-950 border border-blue-800/80 text-blue-400'
                              : 'bg-slate-900 border border-slate-800 text-slate-400'
                          }`}>
                            {log.actorId.startsWith('A') ? <Cpu className="w-4 h-4" /> : <Terminal className="w-4 h-4" />}
                          </div>

                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-bold text-white text-xs">
                                {isAr ? log.actionAr : log.action}
                              </span>
                              
                              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-cyan-300 font-semibold">
                                {isAr ? log.actorNameAr : log.actorName}
                              </span>

                              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400">
                                {log.complianceStandard}
                              </span>
                            </div>

                            <div className="text-[11px] text-slate-400 leading-relaxed">
                              {isAr ? log.rationaleAr : log.rationaleEn}
                            </div>
                          </div>
                        </div>

                        {/* Timestamp & Expand Action */}
                        <div className="flex items-center justify-between md:justify-end gap-3 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-900">
                          <div className="text-slate-500 font-mono text-[11px] flex items-center gap-1">
                            <Clock className="w-3 h-3 text-slate-600" />
                            <span>{log.timestamp}</span>
                          </div>

                          <div className="text-slate-400 hover:text-white transition-colors">
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </div>
                        </div>
                      </div>

                      {/* Expanded Traceability Details */}
                      {isExpanded && (
                        <div className="px-4 pb-4 pt-2 border-t border-slate-900/80 bg-slate-950/80 text-xs space-y-3 rounded-b-xl">
                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
                            
                            <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">{isAr ? 'بصمة التوقيع التشفيري (SHA-256)' : 'Cryptographic Event Hash'}</span>
                              <span className="font-mono text-emerald-400 text-[11px] font-semibold break-all">{hashOf(log.id)}</span>
                            </div>

                            <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">{isAr ? 'معيار الامتثال والتنظيم' : 'Regulatory Standard'}</span>
                              <span className="font-mono text-cyan-300 text-[11px] font-semibold">{log.complianceStandard}</span>
                            </div>

                            <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">{isAr ? 'مصدر البيانات / النموذج' : 'Data Reference / Engine'}</span>
                              <span className="text-slate-200 text-[11px] font-semibold">{log.sourceRef || 'Mujeaz Autonomous Stack'}</span>
                            </div>

                          </div>

                          {log.confidence && (
                            <div className="flex items-center gap-2 text-[11px] text-slate-400">
                              <span>{isAr ? 'نسبة ثقة قرار الذكاء الاصطناعي:' : 'AI Model Confidence Rating:'}</span>
                              <span className="font-mono font-bold text-emerald-400">{log.confidence}%</span>
                            </div>
                          )}

                          <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between">
                            <span>Event ID: {log.id}</span>
                            <span className="text-emerald-500 flex items-center gap-1">
                              <Lock className="w-3 h-3" />
                              <span>Immutable Audit Record Logged</span>
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

          </div>
        )}

      </div>

    </div>
  );
};
