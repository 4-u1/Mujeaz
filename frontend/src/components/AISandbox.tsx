import React, { useState } from 'react';
import { Language } from '../types';
import { api } from '../api/client';
import { 
  Sparkles, 
  FileText, 
  ShieldCheck, 
  AlertTriangle, 
  Send, 
  RefreshCw, 
  FileCode, 
  CheckCircle2,
  Building,
  Activity
} from 'lucide-react';

interface AISandboxProps {
  lang: Language;
}

const PRESET_SAMPLES = [
  {
    titleEn: 'MRI Lumbar Spine L4-L5 (Orthopedic)',
    titleAr: 'رنين مغناطيسي للفقرات القطنية L4-L5',
    text: `Patient 45yo male with 8 weeks of severe lower back pain radiating to left leg. L5 dermatomal numbness. Positive Straight Leg Raise test at 45 degrees. Requesting MRI Lumbar Spine without contrast.`,
  },
  {
    titleEn: 'Secukinumab (Cosentyx) Biologic (Rheumatology)',
    titleAr: 'عقار سيكوكينوماب البيولوجي',
    text: `38yo female with active Psoriatic Arthritis, PASI score 16.5, 8 tender joints. Failed methotrexate 15mg weekly for 12 weeks. History of severe cutaneous allergic eruption to Adalimumab (Humira) 40mg. Requesting Secukinumab 150mg SC.`,
  },
  {
    titleEn: 'CT Abdomen & Pelvis with Contrast (Surgery)',
    titleAr: 'أشعة مقطعية للبطن والحوض مع الصبغة',
    text: `52yo female with 3 days of persistent right lower quadrant abdominal pain, fever 38.5C, leukocytosis WBC 14.5k. Rebound tenderness present. Requesting CT Abdomen/Pelvis with IV contrast to rule out complicated appendicitis.`,
  },
];

export const AISandbox: React.FC<AISandboxProps> = ({ lang }) => {
  const isAr = lang === 'ar';
  const [inputText, setInputText] = useState(PRESET_SAMPLES[0].text);
  const [payerName, setPayerName] = useState('Demo Payer A');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const data = await api.analyzeOrder({ clinicalNoteText: inputText, payerName });
      setResult(data);
    } catch (err: any) {
      console.error('API Error:', err);
      setError(err.message || 'Failed to connect to Mujeaz AI Engine.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl text-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold">
              {isAr ? 'مختبر تحليل الطلبات السريرية بـ Gemini AI' : 'Mujeaz AI Order Analysis Sandbox'}
            </h1>
            <p className="text-xs text-slate-400">
              {isAr ? 'أدخل أي ملاحظة طبية بـ العربية أو الإنجليزية واختبر قدرة مُجاز على الاستخراج ومطابقة السياسات وحساب المخاطر' : 'Test any clinical note or physician order against demo payer rules'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Input Column */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 text-white shadow-xl">
            
            {/* Presets */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">
                {isAr ? 'اختر قالب ملاحظة جاهز للاختبار:' : 'Select Sample Order Preset:'}
              </label>
              <div className="space-y-1.5">
                {PRESET_SAMPLES.map((sample, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInputText(sample.text)}
                    className="w-full text-left p-2.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 transition-colors cursor-pointer"
                  >
                    <div className="font-bold text-emerald-400">{isAr ? sample.titleAr : sample.titleEn}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Payer Select */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-emerald-400" />
                <span>{isAr ? 'شركة التأمين / الجهة الداعمة:' : 'Target Payer / Guidelines:'}</span>
              </label>
              <select
                value={payerName}
                onChange={(e) => setPayerName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
              >
                <option value="Demo Payer A">جهة دافعة تجريبية أ / Demo Payer A</option>
                <option value="Demo Payer B">جهة دافعة تجريبية ب / Demo Payer B</option>
                <option value="Demo Payer C">جهة دافعة تجريبية ج / Demo Payer C</option>
                <option value="Malath Cooperative">ملاذ للتأمين / Malath Insurance</option>
                <option value="Generic payer rules (demo)">قواعد عامة (تجريبية) / Generic rules (demo)</option>
              </select>
            </div>

            {/* Textarea */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-cyan-400" />
                <span>{isAr ? 'نص الملاحظة السريرية (العربية أو الإنجليزية):' : 'Clinical Note Text (Arabic or English):'}</span>
              </label>
              <textarea
                rows={7}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={isAr ? 'اكتب الملاحظة السريرية هنا...' : 'Type clinical note here...'}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-serif leading-relaxed"
              />
            </div>

            {/* Action Button */}
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 text-white font-bold text-xs flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-emerald-950 transition-all"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>{isAr ? 'جارٍ المعالجة بواسطة Gemini AI...' : 'Processing with Gemini AI...'}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-300" />
                  <span>{isAr ? 'تحليل الطلب وتوليد الجاهزية' : 'Analyze Order with Mujeaz AI'}</span>
                </>
              )}
            </button>

          </div>
        </div>

        {/* Results Column */}
        <div className="lg:col-span-7 space-y-4">
          {error && (
            <div className="bg-rose-950 border border-rose-800 rounded-2xl p-4 text-xs text-rose-200">
              ⚠️ {error}
            </div>
          )}

          {!result && !loading && !error && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-3">
              <Activity className="w-12 h-12 text-slate-600 mx-auto" />
              <h3 className="text-base font-bold text-white">
                {isAr ? 'بانتظار إجراء التحليل' : 'Awaiting Clinical Order Analysis'}
              </h3>
              <p className="text-xs max-w-sm mx-auto">
                {isAr ? 'اضغط على "تحليل الطلب" لتشغيل محرك مُجاز واستخراج الحقائق وحساب مؤشر الجاهزية' : 'Click "Analyze Order with Mujeaz AI" to parse facts, evaluate policies, and compute readiness score.'}
              </p>
            </div>
          )}

          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 text-white shadow-2xl animate-fadeIn">

              {result.mode === 'fallback' && (
                <div className="bg-amber-950/50 border border-amber-800/70 rounded-xl p-3 text-xs text-amber-200 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                  <span>{isAr ? result.noticeAr : result.notice}</span>
                </div>
              )}
              
              {/* Score Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <span className="text-xs text-slate-400">{result.mode === 'fallback' ? (isAr ? 'مخرجات عينة (لم يتم التحليل):' : 'Sample output (not analyzed):') : (isAr ? 'مؤشر الجاهزية (حسابه حتمي من نتائج الوكلاء):' : 'Readiness (computed deterministically from agent findings):')}</span>
                  <h2 className="text-xl font-bold text-emerald-400 mt-0.5">
                    {isAr ? result.readinessScore.readinessLabelAr : result.readinessScore.readinessLabel}
                  </h2>
                </div>

                <div className="w-14 h-14 rounded-2xl bg-emerald-950 border border-emerald-800 flex items-center justify-center font-extrabold text-xl text-emerald-400">
                  {result.readinessScore.overallScore}
                </div>
              </div>

              {/* Diagnosis & CPT */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-slate-400">{isAr ? 'التشخيص المستخرج:' : 'Extracted Diagnosis:'}</span>
                  <div className="font-bold text-white mt-1">
                    {result.patientDiagnosis.code} - {isAr ? result.patientDiagnosis.displayAr : result.patientDiagnosis.display}
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-slate-400">{isAr ? 'الإجراء والكلفة المقدرة:' : 'Procedure & Cost:'}</span>
                  <div className="font-bold text-emerald-400 mt-1">
                    {result.procedureCode.code} - {result.procedureCode.costSAR} SAR
                  </div>
                </div>
              </div>

              {/* Clinical Facts */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-slate-300">{isAr ? 'الحقائق السريرية المستخرجة:' : 'Extracted Clinical Facts:'}</h3>
                <div className="space-y-1.5">
                  {result.clinicalFacts.map((fact: any, i: number) => (
                    <div key={i} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs flex items-center justify-between">
                      <span>• {isAr ? fact.factAr : fact.fact}</span>
                      <span className="text-[10px] text-slate-500 font-mono">{fact.confidence}% Confidence</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Warnings */}
              {result.readinessScore.warningNotice && (
                <div className="bg-rose-950/40 p-3.5 rounded-xl border border-rose-900/60 text-xs text-rose-300 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <span>{isAr ? result.readinessScore.warningNoticeAr : result.readinessScore.warningNotice}</span>
                </div>
              )}

            </div>
          )}

        </div>

      </div>

    </div>
  );
};
