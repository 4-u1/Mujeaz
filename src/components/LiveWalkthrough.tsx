import React, { useState } from 'react';
import { ClaimDigitalTwin, Language } from '../types';
import { 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle, 
  Search, 
  ShieldCheck, 
  FileCode, 
  RotateCcw, 
  FileText, 
  Layers,
  ChevronRight,
  Download,
  Copy,
  Check
} from 'lucide-react';

interface LiveWalkthroughProps {
  lang: Language;
  case4922: ClaimDigitalTwin;
  case8103: ClaimDigitalTwin;
  onRunEvidenceHunter: (caseId: string) => void;
  onSelectCase: (caseId: string) => void;
}

export const LiveWalkthrough: React.FC<LiveWalkthroughProps> = ({
  lang,
  case4922,
  case8103,
  onRunEvidenceHunter,
  onSelectCase,
}) => {
  const isAr = lang === 'ar';
  const [activeScenario, setActiveScenario] = useState<'SCENARIO_1' | 'SCENARIO_2'>('SCENARIO_1');
  const [currentStage, setCurrentStage] = useState<number>(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [copied, setCopied] = useState(false);

  // Checks if Case 4922 has been updated by Evidence Hunter
  const isEvidenceFound = case4922.readinessScore.overallScore >= 90;

  const handleNextStage = () => {
    if (currentStage < 7) {
      setIsProcessing(true);
      setTimeout(() => {
        setIsProcessing(false);
        setCurrentStage((prev) => prev + 1);
      }, 500);
    }
  };

  const handleRunHunterInWalkthrough = () => {
    setIsProcessing(true);
    setTimeout(() => {
      onRunEvidenceHunter('case-4922');
      setIsProcessing(false);
      setCurrentStage(4);
    }, 1200);
  };

  const handleCopyAppeal = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-8 pb-12">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 text-xs font-semibold mb-2">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isAr ? 'سيناريوهات العرض الحي المباشرة' : 'Interactive Live Scenario Walkthrough'}</span>
            </div>
            <h1 className="text-2xl font-bold">
              {isAr ? 'رحلة الطلب والمطالبة داخل نظام مُجاز' : 'Complete End-to-End Mujeaz Request & Recovery Journey'}
            </h1>
            <p className="text-slate-400 text-xs mt-1">
              {isAr
                ? 'شاهد كيف يتنبأ مُجاز بمخاطر الرفض، يجد الأدلة في السجل، ويحول الرفض إلى فرصة استرداد.'
                : 'Experience pre-submission denial prevention and post-denial automated appeal generation.'}
            </p>
          </div>

          {/* Scenario Selector Switch */}
          <div className="flex items-center bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs font-semibold">
            <button
              onClick={() => { setActiveScenario('SCENARIO_1'); setCurrentStage(1); }}
              className={`px-4 py-2 rounded-lg transition-all ${
                activeScenario === 'SCENARIO_1'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {isAr ? 'السيناريو 1: منع الرفض (MRI)' : 'Scenario 1: Denial Prevention'}
            </button>
            <button
              onClick={() => setActiveScenario('SCENARIO_2')}
              className={`px-4 py-2 rounded-lg transition-all ${
                activeScenario === 'SCENARIO_2'
                  ? 'bg-amber-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {isAr ? 'السيناريو 2: استرداد الرفض' : 'Scenario 2: Recovery Mode'}
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* SCENARIO 1: PRE-SUBMISSION DENIAL PREVENTION (7 STAGES)   */}
      {/* ========================================================= */}
      {activeScenario === 'SCENARIO_1' && (
        <div className="space-y-6">
          
          {/* Stepper Progress Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <div className="text-xs font-semibold text-slate-400 mb-3 flex items-center justify-between">
              <span>{isAr ? 'المراحل السبع لرحلة الطلب:' : '7-Stage Order Progression Lifecycle:'}</span>
              <span className="text-emerald-400 font-bold">{isAr ? `المرحلة ${currentStage} من 7` : `Stage ${currentStage} of 7`}</span>
            </div>

            <div className="grid grid-cols-7 gap-2">
              {[
                { stage: 1, labelAr: '1. الملاحظة', labelEn: '1. Note' },
                { stage: 2, labelAr: '2. اكتشاف الخطر', labelEn: '2. Risk' },
                { stage: 3, labelAr: '3. صيد الأدلة', labelEn: '3. Hunter' },
                { stage: 4, labelAr: '4. المطابقة', labelEn: '4. Policy' },
                { stage: 5, labelAr: '5. مؤشر الجاهزية', labelEn: '5. Score' },
                { stage: 6, labelAr: '6. معايير نفيس', labelEn: '6. FHIR' },
                { stage: 7, labelAr: '7. حماية الإيراد', labelEn: '7. Protected' },
              ].map((s) => (
                <button
                  key={s.stage}
                  onClick={() => setCurrentStage(s.stage)}
                  className={`p-2 rounded-lg text-[11px] font-semibold text-center transition-all cursor-pointer ${
                    s.stage === currentStage
                      ? 'bg-emerald-600 text-white shadow-lg ring-2 ring-emerald-400'
                      : s.stage < currentStage
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : 'bg-slate-950 text-slate-500 border border-slate-800'
                  }`}
                >
                  <div>{isAr ? s.labelAr : s.labelEn}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Stage Cards Content */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
            
            {/* STAGE 1: Clinical Order Ingestion */}
            {currentStage === 1 && (
              <div className="space-y-4 animate-fadeIn">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-800 flex items-center justify-center text-blue-400 font-bold">
                    1
                  </div>
                  <div>
                    <h3 className="text-lg font-bold">
                      {isAr ? 'المرحلة الأولى: استقبال الطلب السريري' : 'Stage 1: Clinical Order Ingestion'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'طبيب جراحة العظام يكتب طلباً لرنين مغناطيسي للفقرات القطنية L4-L5' : 'Orthopedic surgeon requests MRI Lumbar Spine for Ahmed Al-Harbi'}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-semibold text-white">
                      {isAr ? 'نص الملاحظة الطبية (من نظام المستشفى HIS):' : 'Primary EMR Physician Note:'}
                    </span>
                    <span className="font-mono text-slate-500">Encounter #2081</span>
                  </div>
                  <p className="text-xs text-slate-300 bg-slate-900 p-3 rounded-lg border border-slate-800/80 font-serif leading-relaxed">
                    "{case4922.clinicalNoteText}"
                  </p>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleNextStage}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer shadow-md"
                  >
                    <span>{isAr ? 'الانتقال للتحليل الذكي' : 'Proceed to AI Analysis'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 2: Denial Risk Detection */}
            {currentStage === 2 && (
              <div className="space-y-4 animate-fadeIn">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-rose-950 border border-rose-800 flex items-center justify-center text-rose-400 font-bold">
                    2
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-rose-300 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-rose-400 animate-bounce" />
                      <span>{isAr ? 'المرحلة الثانية: اكتشاف مخاطر الرفض' : 'Stage 2: Denial Risk Detected'}</span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'مُجاز يتنبأ بمخاطر الرفض بنسبة 78% قبل إرسال الطلب' : 'Mujeaz AI detects 78% denial risk before submission'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-rose-950/40 p-4 rounded-xl border border-rose-900/60 space-y-2">
                    <div className="text-xs font-bold text-rose-300 uppercase tracking-wider">
                      🔴 {isAr ? 'سبب الخطر المكتشف:' : 'Denial Risk Cause:'}
                    </div>
                    <p className="text-xs text-rose-200">
                      {case4922.readinessScore.warningNotice}
                    </p>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                    <div className="text-xs text-slate-400 font-semibold">{isAr ? 'التقييم المالي للأثر:' : 'Financial Risk Impact:'}</div>
                    <div className="text-xl font-extrabold text-rose-400">
                      378,000 SAR <span className="text-xs text-slate-400 font-normal">Revenue at Risk</span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Mujeaz Readiness Score: <span className="font-bold text-amber-400">74 / 100</span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center pt-2">
                  <span className="text-xs text-slate-400">
                    {isAr ? 'الانتقال إلى تشغيل وكيل صيد الأدلة في السجل' : 'Trigger Evidence Hunter Agent'}
                  </span>
                  <button
                    onClick={handleRunHunterInWalkthrough}
                    disabled={isProcessing}
                    className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 text-white font-extrabold text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-emerald-950"
                  >
                    <Sparkles className="w-4 h-4 text-amber-300" />
                    <span>{isProcessing ? (isAr ? 'جارٍ المسح...' : 'Searching EMR...') : (isAr ? 'تشغيل صيد الأدلة (Find Evidence)' : 'Run Evidence Hunter')}</span>
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 3: Evidence Hunter Execution */}
            {currentStage === 3 && (
              <div className="space-y-4 animate-fadeIn">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400 font-bold">
                    3
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-cyan-300">
                      {isAr ? 'المرحلة الثالثة: وكيل صيد الأدلة (Evidence Hunter)' : 'Stage 3: Evidence Hunter Agent Active'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'البحث التلقائي داخل السجل الطبي عن الأدلة الناقصة دون إجهاد الطبيب' : 'Deep-scanning patient medical history for conservative therapy proof'}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="text-xs font-bold text-emerald-400 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>✓ Evidence Found in EMR Records:</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                      <div className="font-bold text-white">✓ 6 Physiotherapy Sessions</div>
                      <div className="text-slate-400 text-[11px]">Source: Rehabilitation Encounter #1820</div>
                      <div className="text-emerald-400 text-[10px] mt-1 font-mono">Date: 2026-06-11</div>
                    </div>

                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                      <div className="font-bold text-white">✓ NSAID Prescription (Celecoxib 200mg)</div>
                      <div className="text-slate-400 text-[11px]">Source: Outpatient Pharmacy Log #0912</div>
                      <div className="text-emerald-400 text-[10px] mt-1 font-mono">Date: 2026-05-28</div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleNextStage}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer"
                  >
                    <span>{isAr ? 'مطابقة السياسات ومراجعة النتيجة' : 'Re-evaluate Policy Conformance'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 4: Policy Reasoning Re-evaluation */}
            {currentStage === 4 && (
              <div className="space-y-4 animate-fadeIn">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400 font-bold">
                    4
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-emerald-300">
                      {isAr ? 'المرحلة الرابعة: مطابقة السياسة بعد ربط الأدلة' : 'Stage 4: Policy Reasoning Updated'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'Policy Reasoning Agent يحدث حالة القواعد إلى: مستوفاة بالكامل' : 'Policy Agent updates coverage requirement to "SATISFIED"'}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-emerald-900/60 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200">
                      Tawuniya Policy TAW-LUMBAR-POL-04 (6-Week Physio)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                      Requirement: Satisfied
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    {isAr
                      ? 'تم ربط جلسات العلاج الطبيعي الموثقة بطلب الرنين المغناطيسي تلقائياً.'
                      : 'Physiotherapy sessions from Encounter #1820 attached as clinical evidence.'}
                  </p>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleNextStage}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer"
                  >
                    <span>{isAr ? 'حساب مؤشر الجاهزية النهائي' : 'View Readiness Score'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 5: Mujeaz Readiness Score™ = 98/100 */}
            {currentStage === 5 && (
              <div className="space-y-4 animate-fadeIn">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400 font-bold text-lg">
                    98
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-emerald-400 flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <span>Mujeaz Readiness Score™: 98 / 100</span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'الطلب أصبح الآن جاهزاً للقرار (Decision-Ready)' : 'Authorization request is now Decision-Ready for Payer submission'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-center text-xs">
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">{isAr ? 'الأدلة السريرية' : 'Clinical Evidence'}</div>
                    <div className="font-bold text-emerald-400 mt-1">98%</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">{isAr ? 'مطابقة السياسة' : 'Policy Match'}</div>
                    <div className="font-bold text-emerald-400 mt-1">96%</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">{isAr ? 'التوثيق' : 'Documentation'}</div>
                    <div className="font-bold text-emerald-400 mt-1">97%</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">{isAr ? 'سلامة الترميز' : 'Coding Integrity'}</div>
                    <div className="font-bold text-emerald-400 mt-1">100%</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">{isAr ? 'المرفقات المطلوب' : 'Attachments'}</div>
                    <div className="font-bold text-emerald-400 mt-1">99%</div>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                    <div className="text-slate-400 text-[10px]">{isAr ? 'الاكتمال الإداري' : 'Administrative'}</div>
                    <div className="font-bold text-emerald-400 mt-1">100%</div>
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleNextStage}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer"
                  >
                    <span>{isAr ? 'التحقق من معايير نفيس FHIR' : 'Check FHIR Conformance'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 6: FHIR / NPHIES Conformance Passed */}
            {currentStage === 6 && (
              <div className="space-y-4 animate-fadeIn">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-950 border border-purple-800 flex items-center justify-center text-purple-400 font-bold">
                    6
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-purple-300">
                      {isAr ? 'المرحلة السادسة: التحقق من معايير FHIR ونفيس' : 'Stage 6: FHIR / NPHIES Conformance Passed'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {isAr ? 'A4 Conformance Agent يبني الهيكل الموحد المعتمد قبل البث' : 'FHIR CoverageEligibilityRequest payload validated'}
                    </p>
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[11px] text-slate-300 max-h-48 overflow-y-auto">
                  <pre>{case4922.fhirPayload.rawJson}</pre>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={handleNextStage}
                    className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer"
                  >
                    <span>{isAr ? 'إرسال وحماية الإيراد' : 'Submit & Protect Revenue'}</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STAGE 7: Authorization Submitted & Protected Revenue */}
            {currentStage === 7 && (
              <div className="space-y-4 animate-fadeIn text-center py-6">
                <div className="w-16 h-16 rounded-full bg-emerald-950 border-2 border-emerald-500 flex items-center justify-center mx-auto text-emerald-400">
                  <CheckCircle2 className="w-10 h-10" />
                </div>

                <h3 className="text-2xl font-extrabold text-white">
                  {isAr ? 'تم حماية الإيراد بنجاح! (Revenue Protected)' : 'Authorization Approved & Revenue Protected!'}
                </h3>

                <p className="text-slate-300 text-xs max-w-md mx-auto">
                  {isAr
                    ? 'تم منع الرفض المحتمل وحماية مبلغ 15,500 ريال للإجراء (و378,000 ريال إجمالي الحزمة والمعرضة للخطر).'
                    : 'Potential 78% denial risk eliminated prior to submission. Procedure value 15,500 SAR protected.'}
                </p>

                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-400 font-bold text-sm">
                  <span>Mujeaz Status: APPROVED & PROTECTED</span>
                </div>

                <div className="pt-4 flex justify-center gap-3">
                  <button
                    onClick={() => { setActiveScenario('SCENARIO_2'); }}
                    className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center gap-2 cursor-pointer shadow-lg"
                  >
                    <span>{isAr ? 'الانتقال إلى السيناريو 2: استرداد الرفض' : 'Switch to Scenario 2: Denial Recovery'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

          </div>

        </div>
      )}

      {/* ========================================================= */}
      {/* SCENARIO 2: DENIED CLAIM RECOVERY MODE (A6 RECOVERY AGENT)*/}
      {/* ========================================================= */}
      {activeScenario === 'SCENARIO_2' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white space-y-6">
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-950 border border-amber-800 flex items-center justify-center text-amber-400">
                <RotateCcw className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-amber-300">
                  {isAr ? 'سيناريو الرفض: محرك استرداد الإيرادات (Recovery Mode)' : 'Denied Claim Recovery Mode'}
                </h2>
                <p className="text-xs text-slate-400">
                  {isAr ? 'تحليل سبب الرفض، ربط الاستثناءات السريرية، وبناء خطة استئناف محكمة' : 'Root cause analysis & automated formal appeal generation'}
                </p>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs text-slate-400">{isAr ? 'المبلغ المسترد المحتمل:' : 'Recoverable Value:'}</span>
              <div className="text-xl font-bold text-cyan-400">144,000 SAR</div>
            </div>
          </div>

          {/* Denial Info Banner */}
          <div className="bg-rose-950/40 border border-rose-900/60 rounded-xl p-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-rose-300">
                🔴 DENIAL RECEIVED: Code DEN-STEP-04
              </span>
              <span className="text-rose-400 font-mono">Claim #{case8103.claimNumber}</span>
            </div>
            <p className="text-xs text-slate-300">
              {isAr ? case8103.appealPackage?.denialReasonAr : case8103.appealPackage?.denialReason}
            </p>
          </div>

          {/* Root Cause & Found Evidence Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Root Cause */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-amber-400">
                {isAr ? 'تحليل السبب الجذر (Root Cause Analysis):' : 'Root Cause Analysis:'}
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {isAr ? case8103.appealPackage?.rootCauseAr : case8103.appealPackage?.rootCause}
              </p>
            </div>

            {/* Strategy */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-emerald-400">
                {isAr ? 'استراتيجية الاستئناف المحكمة (Appeal Strategy):' : 'Appeal Strategy:'}
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {isAr ? case8103.appealPackage?.appealStrategyAr : case8103.appealPackage?.appealStrategy}
              </p>
              <div className="text-[11px] text-emerald-400 font-bold">
                {isAr ? 'قوة حجة الاستئناف:' : 'Appeal Strength:'} {case8103.appealPackage?.appealStrength}%
              </div>
            </div>

          </div>

          {/* Generated Formal Appeal Letter Box */}
          <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-400" />
                <span>{isAr ? 'خطاب إعادة النظر الموثق الصادر عن المساعد الذكي:' : 'Formal Reconsideration & Appeal Letter:'}</span>
              </span>

              <button
                onClick={() => handleCopyAppeal(isAr ? case8103.appealPackage?.formalLetterAr! : case8103.appealPackage?.formalLetterEn!)}
                className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? (isAr ? 'تم النسخ!' : 'Copied!') : (isAr ? 'نسخ الخطاب' : 'Copy Letter')}</span>
              </button>
            </div>

            <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 font-serif text-xs text-slate-200 leading-relaxed whitespace-pre-line max-h-64 overflow-y-auto">
              {isAr ? case8103.appealPackage?.formalLetterAr : case8103.appealPackage?.formalLetterEn}
            </div>
          </div>

        </div>
      )}

    </div>
  );
};
