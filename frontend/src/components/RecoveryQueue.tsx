import React, { useState } from 'react';
import { ClaimDigitalTwin, Language } from '../types';
import { 
  RotateCcw, 
  Sparkles, 
  FileText, 
  Copy, 
  Check, 
  ShieldCheck, 
  AlertTriangle, 
  ChevronRight,
  TrendingUp,
  Download
} from 'lucide-react';

interface RecoveryQueueProps {
  cases: ClaimDigitalTwin[];
  lang: Language;
  onSelectCase: (caseId: string) => void;
}

export const RecoveryQueue: React.FC<RecoveryQueueProps> = ({ cases, lang, onSelectCase }) => {
  const isAr = lang === 'ar';
  const deniedCases = cases.filter((c) => c.status === 'DENIED' || c.status === 'RECOVERY_IN_PROGRESS' || c.status === 'APPEAL_READY');
  const [selectedCase, setSelectedCase] = useState<ClaimDigitalTwin | null>(deniedCases[0] || null);
  const [copied, setCopied] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [appealResult, setAppealResult] = useState<any | null>(null);

  const formatSAR = (val: number) => {
    return new Intl.NumberFormat(isAr ? 'ar-SA' : 'en-US', {
      style: 'currency',
      currency: 'SAR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const handleTriggerAppeal = async () => {
    if (!selectedCase) return;
    setIsGenerating(true);

    try {
      const response = await fetch('/api/ai/generate-appeal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Send only what the Recovery Agent needs (data minimisation): no patient name or ID.
        body: JSON.stringify({
          claimNumber: selectedCase.claimNumber,
          payerName: selectedCase.payerName,
          requestedService: selectedCase.requestedService,
          clinicalNoteText: selectedCase.clinicalNoteText,
          denialReason: selectedCase.appealPackage?.denialReason,
          evidence: selectedCase.appealPackage?.foundEvidence?.map((e) => ({ fact: e.fact, source: e.source, date: e.date })),
          appealPackage: selectedCase.appealPackage,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAppealResult(data);
      }
    } catch (err) {
      console.error('Error generating appeal:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 pb-12">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-950 border border-amber-800 flex items-center justify-center text-amber-400">
              <RotateCcw className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold">
                {isAr ? 'قائمة الاسترداد وإدارة الاستئناف' : 'Revenue Recovery Queue & Appeal Center'}
              </h1>
              <p className="text-xs text-slate-400">
                {isAr ? 'إعادة تحليل المطالبات المرفوضة، صيد الأدلة الناقصة، وإصدار حزم الاستئناف الموثقة' : 'Automated denial root cause analysis and evidence-backed reconsideration packages'}
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-xs text-slate-400">{isAr ? 'إجمالي القيمة القابلة للاسترداد:' : 'Total Recoverable Value:'}</span>
            <div className="text-xl font-bold text-cyan-400">
              {formatSAR(deniedCases.reduce((acc, c) => acc + (c.revenueRisk.recoverableValue || 0), 0))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Denied Claims List Sidebar */}
        <div className="lg:col-span-4 space-y-3">
          <h2 className="text-sm font-bold text-slate-300">{isAr ? 'المطالبات المرفوضة المعلقة:' : 'Denied Claims Pending Appeal:'}</h2>
          
          <div className="space-y-2">
            {deniedCases.map((c) => (
              <div
                key={c.id}
                onClick={() => { setSelectedCase(c); setAppealResult(null); }}
                className={`p-4 rounded-xl border transition-all cursor-pointer ${
                  selectedCase?.id === c.id
                    ? 'bg-amber-950/40 border-amber-600/80 shadow-lg text-white'
                    : 'bg-slate-900 border-slate-800 hover:bg-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-bold text-amber-400">{c.claimNumber}</span>
                  <span className="text-[11px] font-mono text-slate-400">{c.payerName}</span>
                </div>

                <div className="font-semibold text-xs text-white">
                  {isAr ? c.requestedServiceAr : c.requestedService}
                </div>

                <div className="flex items-center justify-between mt-2 text-[11px]">
                  <span className="text-slate-400">{c.patientName}</span>
                  <span className="font-bold text-rose-400">{formatSAR(c.revenueRisk.financialValue)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Case Appeal Details */}
        <div className="lg:col-span-8 space-y-4">
          {selectedCase && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-white space-y-6 shadow-2xl">
              
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <div className="text-xs text-slate-400">{isAr ? 'حالة الاسترداد المعالجة:' : 'Processing Recovery Twin:'}</div>
                  <h2 className="text-xl font-bold text-amber-300">{selectedCase.claimNumber}</h2>
                </div>

                <button
                  onClick={handleTriggerAppeal}
                  disabled={isGenerating}
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer shadow-md"
                >
                  <Sparkles className="w-4 h-4 text-white" />
                  <span>{isGenerating ? (isAr ? 'جارٍ إعادة التوليد...' : 'Compiling Appeal...') : (isAr ? 'إعادة توليد حزمة الاستئناف' : 'Regenerate Appeal AI')}</span>
                </button>
              </div>

              {/* Root Cause Analysis */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="text-xs font-bold text-amber-400">
                  {isAr ? 'سبب الرفض والتحليل السريري المباشر:' : 'Denial Cause & Root Analysis:'}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {isAr ? selectedCase.appealPackage?.rootCauseAr : selectedCase.appealPackage?.rootCause}
                </p>
              </div>

              {appealResult?.mode === 'fallback' && (
                <div className="bg-amber-950/50 border border-amber-800/70 rounded-xl p-3 text-[11px] text-amber-200">
                  {isAr ? appealResult.noticeAr : appealResult.notice}
                </div>
              )}

              {/* Strategy */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="text-xs font-bold text-emerald-400">
                  {isAr ? 'استراتيجية الاستئناف المقترحة (A6 Recovery Agent):' : 'A6 Recovery Strategy:'}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {appealResult ? (isAr ? appealResult.appealStrategyAr : appealResult.appealStrategy) : (isAr ? selectedCase.appealPackage?.appealStrategyAr : selectedCase.appealPackage?.appealStrategy)}
                </p>
              </div>

              {/* Formal Letter Display */}
              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-emerald-400" />
                    <span>{isAr ? 'خطاب الاستئناف وإعادة النظر الموثق:' : 'Formal Reconsideration Appeal Letter:'}</span>
                  </span>

                  <button
                    onClick={() => handleCopy(appealResult ? (isAr ? appealResult.formalLetterAr : appealResult.formalLetterEn) : (isAr ? selectedCase.appealPackage?.formalLetterAr! : selectedCase.appealPackage?.formalLetterEn!))}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied!' : (isAr ? 'نسخ الخطاب' : 'Copy Letter')}</span>
                  </button>
                </div>

                <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 font-serif text-xs text-slate-200 leading-relaxed whitespace-pre-line max-h-72 overflow-y-auto">
                  {appealResult 
                    ? (isAr ? appealResult.formalLetterAr : appealResult.formalLetterEn)
                    : (isAr ? selectedCase.appealPackage?.formalLetterAr : selectedCase.appealPackage?.formalLetterEn)
                  }
                </div>
              </div>

            </div>
          )}
        </div>

      </div>

    </div>
  );
};
