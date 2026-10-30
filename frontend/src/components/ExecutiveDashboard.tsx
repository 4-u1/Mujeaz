import React, { useState } from 'react';
import { ClaimDigitalTwin, CommandCenterMetrics, Language } from '../types';
import {
  Lock,
  TrendingUp, 
  AlertTriangle, 
  RotateCcw, 
  ShieldCheck, 
  Clock, 
  Layers, 
  ChevronRight, 
  Filter, 
  Search, 
  Sparkles, 
  ArrowUpRight,
  CheckCircle2,
  XCircle,
  AlertCircle,
  FileCheck
} from 'lucide-react';

interface ExecutiveDashboardProps {
  /** null when the signed-in role has no metrics:read permission. */
  metrics: CommandCenterMetrics | null;
  cases: ClaimDigitalTwin[];
  lang: Language;
  onSelectCase: (caseId: string) => void;
  onNavigateTab: (tab: any) => void;
  onRunEvidenceHunter: (caseId: string) => void;
}

export const ExecutiveDashboard: React.FC<ExecutiveDashboardProps> = ({
  metrics,
  cases,
  lang,
  onSelectCase,
  onNavigateTab,
  onRunEvidenceHunter,
}) => {
  const isAr = lang === 'ar';
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredCases = cases.filter((c) => {
    const matchesQuery = 
      c.claimNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.patientName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.requestedService.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.doctorName.toLowerCase().includes(searchQuery.toLowerCase());

    if (statusFilter === 'ALL') return matchesQuery;
    if (statusFilter === 'RISK') return matchesQuery && c.status === 'RISK_DETECTED';
    if (statusFilter === 'DENIED') return matchesQuery && (c.status === 'DENIED' || c.status === 'RECOVERY_IN_PROGRESS' || c.status === 'APPEAL_READY');
    if (statusFilter === 'APPROVED') return matchesQuery && c.status === 'APPROVED';
    return matchesQuery;
  });

  const formatSAR = (amount: number) => {
    return new Intl.NumberFormat(isAr ? 'ar-SA' : 'en-US', {
      style: 'currency',
      currency: 'SAR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="space-y-8 pb-12">
      
      {/* Executive Tagline Hero Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 md:p-8 border border-slate-700/80 shadow-2xl text-white">
        <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-20 -top-20 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-slate-950/90 border border-emerald-500/40 shadow-xl shadow-emerald-950/60 flex items-center justify-center shrink-0 overflow-hidden ring-1 ring-emerald-400/20">
              <img 
                src="/logo_full.png" 
                alt="Mujeaz Official Logo" 
                className="h-full w-full object-cover"
                referrerPolicy="no-referrer"
              />
            </div>
            
            <div className="space-y-2.5 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>{isAr ? 'محرك حماية الإيرادات التشغيلي' : 'AI Revenue Assurance Operating Stack'}</span>
              </div>
              
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight leading-tight">
                {isAr ? (
                  <>مُجاز: <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300 bg-clip-text text-transparent">نمنع الرفض. نحمي الإيراد. نستعيد المفقود.</span></>
                ) : (
                  <>Mujeaz: <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300 bg-clip-text text-transparent">Prevent the denial. Protect the revenue. Recover the lost.</span></>
                )}
              </h1>
              
              <p className="text-slate-300 text-sm md:text-base leading-relaxed">
                {isAr
                  ? 'مركز التحكم الذكي لتحويل الطلبات الطبية إلى موافقات جاهزة للقرار وحماية إيرادات المستشفيات من التسرب والتأخير.'
                  : 'Decision-ready healthcare revenue command center connecting clinical EMR, payer policy reasoning, and appeal recovery.'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap md:flex-col gap-3 min-w-[200px]">
            <button
              onClick={() => onNavigateTab('walkthrough')}
              className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold text-xs md:text-sm shadow-lg shadow-emerald-950 transition-all transform hover:-translate-y-0.5 cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isAr ? 'بدء العرض الحي التفاعلي' : 'Launch Live Walkthrough'}</span>
            </button>
            
            <button
              onClick={() => onNavigateTab('sandbox')}
              className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs md:text-sm font-semibold border border-slate-600/60 transition-all cursor-pointer"
            >
              <FileCheck className="w-4 h-4 text-cyan-400" />
              <span>{isAr ? 'اختبار طلب سريري جديد' : 'Analyze Custom Order'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards Bar — hidden (not zeroed) when the role cannot read financial metrics */}
      {!metrics && (
        <div className="flex items-start gap-3 bg-slate-900/90 rounded-xl p-4 border border-slate-800 text-xs text-slate-300">
          <Lock className="w-4 h-4 shrink-0 text-slate-400 mt-0.5" />
          <span>
            {isAr
              ? 'المؤشرات المالية متاحة لموظف الموافقات ومدير دورة الإيرادات والمدقق فقط. دورك يعرض قائمة الحالات أدناه.'
              : 'Financial metrics are available to authorization officers, RCM managers and auditors. Your role shows the case list below.'}
          </span>
        </div>
      )}
      {metrics && (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        
        {/* Revenue Protected */}
        <div className="bg-slate-900/90 rounded-xl p-4 border border-emerald-900/40 shadow-lg relative overflow-hidden group hover:border-emerald-500/50 transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">{isAr ? 'الإيراد المحمي اليوم' : 'Revenue Protected Today'}</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-950/80 border border-emerald-800/60 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-emerald-400 tracking-tight">
            {formatSAR(metrics.revenueProtectedTodaySAR)}
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-500 font-medium">
            <TrendingUp className="w-3 h-3" />
            <span>+18.4% {isAr ? 'عن المتوسط' : 'vs avg'}</span>
          </div>
        </div>

        {/* Revenue at Risk */}
        <div className="bg-slate-900/90 rounded-xl p-4 border border-rose-900/40 shadow-lg relative overflow-hidden group hover:border-rose-500/50 transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">{isAr ? 'الإيراد المعرض للخطر' : 'Revenue at Risk'}</span>
            <div className="w-8 h-8 rounded-lg bg-rose-950/80 border border-rose-800/60 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-rose-400 tracking-tight">
            {formatSAR(metrics.revenueAtRiskSAR)}
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-rose-400 font-medium">
            <AlertCircle className="w-3 h-3" />
            <span>{isAr ? 'ينتظر صيد الأدلة' : 'Requires evidence hunt'}</span>
          </div>
        </div>

        {/* Revenue Recovered */}
        <div className="bg-slate-900/90 rounded-xl p-4 border border-cyan-900/40 shadow-lg relative overflow-hidden group hover:border-cyan-500/50 transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">{isAr ? 'الإيراد المسترد' : 'Revenue Recovered'}</span>
            <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
              <RotateCcw className="w-4 h-4" />
            </div>
          </div>
          <div className="text-xl font-bold text-cyan-400 tracking-tight">
            {formatSAR(metrics.revenueRecoveredSAR)}
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-cyan-400 font-medium">
            <TrendingUp className="w-3 h-3" />
            <span>{isAr ? 'من مسار الاستئناف' : 'Via recovery appeals'}</span>
          </div>
        </div>

        {/* Prevented Denials */}
        <div className="bg-slate-900/90 rounded-xl p-4 border border-indigo-900/40 shadow-lg relative overflow-hidden group hover:border-indigo-500/50 transition-all">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">{isAr ? 'الرفض الممنوع' : 'Prevented Denials'}</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-950/80 border border-indigo-800/60 flex items-center justify-center text-indigo-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-indigo-300 tracking-tight">
            {metrics.preventedDenialsCount} <span className="text-xs font-normal text-slate-400">{isAr ? 'حالة' : 'cases'}</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-slate-400 font-medium">
            <span>{isAr ? 'قبل الإرسال النهائي' : 'Pre-submission'}</span>
          </div>
        </div>

        {/* Clean Pass Rate */}
        <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">{isAr ? 'نسبة النظافة من المرة الأولى' : 'First-Pass Clean Rate'}</span>
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-300">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-400 tracking-tight">
            {metrics.cleanPassRate}%
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-slate-400 font-medium">
            <span>{isAr ? 'مؤشر الجاهزية متوسط' : 'Avg Readiness:'} {metrics.averageReadinessScore}/100</span>
          </div>
        </div>

        {/* Recovery Queue Count */}
        <div className="bg-slate-900/90 rounded-xl p-4 border border-amber-900/40 shadow-lg relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">{isAr ? 'قائمة الاسترداد' : 'Recovery Queue'}</span>
            <div className="w-8 h-8 rounded-lg bg-amber-950/80 border border-amber-800/60 flex items-center justify-center text-amber-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-amber-400 tracking-tight">
            {metrics.recoveryQueueCount} <span className="text-xs font-normal text-slate-400">{isAr ? 'مطالبة' : 'claims'}</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-amber-500 font-medium">
            <span>{isAr ? 'تتطلب مراجعة بشرية' : 'Pending human review'}</span>
          </div>
        </div>

      </div>
      )}

      {/* Main Content Area: Cases List & Digital Twin Explorer */}
      <div className="bg-slate-900/90 rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
        
        {/* Table Header & Search */}
        <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-emerald-400" />
              <span>{isAr ? 'مركز قيادة الحالات والطلبات الطبية' : 'Authorization & Revenue Command Table'}</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {isAr ? 'عرض متكامل للطلبات السريرية، مؤشر الجاهزية Mujeaz Readiness Score، وتقييم المخاطر المالية' : 'Integrated view of clinical orders, readiness scores, and revenue risk assessment'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder={isAr ? 'بحث عن طالب، مريض، كود...' : 'Search patient, claim, code...'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            {/* Filter Buttons */}
            <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                onClick={() => setStatusFilter('ALL')}
                className={`px-2.5 py-1 rounded-md transition-colors ${statusFilter === 'ALL' ? 'bg-slate-800 text-white font-medium' : 'text-slate-400 hover:text-white'}`}
              >
                {isAr ? 'الكل' : 'All'}
              </button>
              <button
                onClick={() => setStatusFilter('RISK')}
                className={`px-2.5 py-1 rounded-md transition-colors ${statusFilter === 'RISK' ? 'bg-rose-950 text-rose-300 font-medium' : 'text-slate-400 hover:text-white'}`}
              >
                {isAr ? 'مخاطر عالية' : 'High Risk'}
              </button>
              <button
                onClick={() => setStatusFilter('DENIED')}
                className={`px-2.5 py-1 rounded-md transition-colors ${statusFilter === 'DENIED' ? 'bg-amber-950 text-amber-300 font-medium' : 'text-slate-400 hover:text-white'}`}
              >
                {isAr ? 'مرفوض/استرداد' : 'Denied/Recovery'}
              </button>
              <button
                onClick={() => setStatusFilter('APPROVED')}
                className={`px-2.5 py-1 rounded-md transition-colors ${statusFilter === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 font-medium' : 'text-slate-400 hover:text-white'}`}
              >
                {isAr ? 'معتمد' : 'Approved'}
              </button>
            </div>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="p-4">{isAr ? 'رقم الطلب / المريض' : 'Claim / Patient'}</th>
                <th className="p-4">{isAr ? 'الإجراء / كود CPT' : 'Requested Procedure'}</th>
                <th className="p-4">{isAr ? 'الشركة / الجهة' : 'Payer'}</th>
                <th className="p-4">{isAr ? 'مؤشر الجاهزية' : 'Readiness Score'}</th>
                <th className="p-4">{isAr ? 'الإيراد المعرض للخطر' : 'Revenue at Risk'}</th>
                <th className="p-4">{isAr ? 'الحالة التشغيلية' : 'Status'}</th>
                <th className="p-4 text-center">{isAr ? 'إجراءات' : 'Actions'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredCases.map((c) => {
                const isHighRisk = c.revenueRisk.denialRiskPercentage > 50;
                const isDenied = c.status === 'DENIED' || c.status === 'RECOVERY_IN_PROGRESS';
                const isApproved = c.status === 'APPROVED';

                return (
                  <tr key={c.id} className="hover:bg-slate-800/50 transition-colors">
                    
                    {/* Claim / Patient */}
                    <td className="p-4">
                      <div className="font-bold text-white text-sm">{c.claimNumber}</div>
                      <div className="text-slate-400 font-medium">{c.patientName}</div>
                      <div className="text-[11px] text-slate-500">{c.facilityName}</div>
                    </td>

                    {/* Procedure */}
                    <td className="p-4">
                      <div className="font-semibold text-slate-200">{isAr ? c.requestedServiceAr : c.requestedService}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px]">
                          CPT {c.cptCode}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-mono text-[10px]">
                          ICD-10 {c.icd10Code}
                        </span>
                      </div>
                    </td>

                    {/* Payer */}
                    <td className="p-4">
                      <div className="font-medium text-slate-300">{c.payerName}</div>
                      <div className="text-[11px] text-slate-500 font-mono">{c.payerCode}</div>
                    </td>

                    {/* Readiness Score */}
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                          c.readinessScore.overallScore >= 90
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : c.readinessScore.overallScore >= 70
                            ? 'bg-amber-950 text-amber-400 border border-amber-800'
                            : 'bg-rose-950 text-rose-400 border border-rose-800'
                        }`}>
                          {c.readinessScore.overallScore}
                        </div>
                        <div>
                          <div className="font-semibold text-white">
                            {isAr ? c.readinessScore.readinessLabelAr : c.readinessScore.readinessLabel}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            {c.readinessScore.overallScore}/100
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Revenue at Risk */}
                    <td className="p-4">
                      <div className="font-bold text-rose-400 text-sm">
                        {formatSAR(c.revenueRisk.revenueAtRisk)}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {isAr ? 'مخاطر الرفض:' : 'Risk:'} <span className="font-semibold text-rose-300">{c.revenueRisk.denialRiskPercentage}%</span>
                      </div>
                    </td>

                    {/* Status Badge */}
                    <td className="p-4">
                      {isApproved && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400 text-[11px] font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {isAr ? 'معتمد - محمي' : 'Approved'}
                        </span>
                      )}
                      {isHighRisk && !isDenied && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-950 border border-rose-800 text-rose-400 text-[11px] font-semibold animate-pulse">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          {isAr ? 'مخاطر رفض عالية' : 'Risk Detected'}
                        </span>
                      )}
                      {isDenied && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-950 border border-amber-800 text-amber-400 text-[11px] font-semibold">
                          <RotateCcw className="w-3.5 h-3.5" />
                          {isAr ? 'مرفوض - جاهز للاستئناف' : 'Denied / Appeal'}
                        </span>
                      )}
                    </td>

                    {/* Action Buttons */}
                    <td className="p-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        
                        {/* Evidence Hunter Trigger Button if High Risk */}
                        {c.status === 'RISK_DETECTED' && (
                          <button
                            onClick={() => onRunEvidenceHunter(c.id)}
                            className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold flex items-center gap-1 shadow-md shadow-emerald-950 transition-all cursor-pointer"
                            title={isAr ? 'تشغيل وكيل صيد الأدلة لمسح السجل الطبي' : 'Run Evidence Hunter'}
                          >
                            <Sparkles className="w-3 h-3 text-amber-300" />
                            <span>{isAr ? 'صيد الأدلة' : 'Find Evidence'}</span>
                          </button>
                        )}

                        {/* Inspect Digital Twin */}
                        <button
                          onClick={() => onSelectCase(c.id)}
                          className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold border border-slate-700 flex items-center gap-1 transition-colors cursor-pointer"
                        >
                          <span>{isAr ? 'التوأم الرقمي' : 'Inspect Twin'}</span>
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      </div>
                    </td>

                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

      </div>

      {/* Philosophy & Architecture Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        <div className="bg-slate-900/80 rounded-xl p-5 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-white text-sm">
            {isAr ? 'مبدأ: لا دليل = لا مطالبة' : 'Principle: "No Evidence, No Claim"'}
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            {isAr
              ? 'مُجاز لا يخترع أي معلومة سريرية. كل حقيقة تتضمن الحقيقة + المصدر من السجل + التاريخ + نسبة الثقة.'
              : 'Mujeaz strictly forbids hallucinated facts. Every clinical evidence entry links directly to encounter ID, date, and source record.'}
          </p>
        </div>

        <div className="bg-slate-900/80 rounded-xl p-5 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-blue-950 border border-blue-800 flex items-center justify-center text-blue-400">
            <Layers className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-white text-sm">
            {isAr ? 'معمارية الوكلاء الستة (6-Agent Stack)' : 'Multi-Agent Command Stack'}
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            {isAr
              ? 'وكلاء متعددو المهام: الفهم السريري، صيد الأدلة، مطابقة السياسات، معايير نفيس، مخاطر الإيراد، ومحرك الاسترداد.'
              : 'Dedicated agents work in harmony to parse orders, hunt physical EMR evidence, evaluate payer rules, and automate appeals.'}
          </p>
        </div>

        <div className="bg-slate-900/80 rounded-xl p-5 border border-slate-800 space-y-2">
          <div className="w-8 h-8 rounded-lg bg-amber-950 border border-amber-800 flex items-center justify-center text-amber-400">
            <RotateCcw className="w-4 h-4" />
          </div>
          <h3 className="font-bold text-white text-sm">
            {isAr ? 'التوأم الرقمي للإيراد الصحي' : 'Healthcare Revenue Digital Twin'}
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            {isAr
              ? 'تمثيل حقيقي ككيان رقمي حي يبين قيمة الإيراد، نسبة الخطر، القيمة القابلة للاسترداد، وحزم الاستئناف جاهزة المراجعة.'
              : 'Real-time digital twin representation mapping clinical events to payer decisions, FHIR payloads, and appeal packages.'}
          </p>
        </div>

      </div>

    </div>
  );
};
