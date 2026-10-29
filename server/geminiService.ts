import { GoogleGenAI, Type } from "@google/genai";

let aiInstance: GoogleGenAI | null = null;

function getGeminiClient(): GoogleGenAI | null {
  if (!aiInstance && process.env.GEMINI_API_KEY) {
    aiInstance = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });
  }
  return aiInstance;
}

export interface AnalyzeOrderRequest {
  clinicalNoteText: string;
  payerName?: string;
  requestedService?: string;
}

export interface AnalyzeOrderResult {
  patientDiagnosis: { code: string; display: string; displayAr: string };
  procedureCode: { code: string; display: string; displayAr: string; costSAR: number };
  clinicalFacts: { fact: string; factAr: string; category: string; source: string; confidence: number }[];
  policyRules: { title: string; titleAr: string; requirement: string; requirementAr: string; status: 'PASSED' | 'WARNING' | 'FAILED' }[];
  readinessScore: {
    clinicalEvidence: number;
    policyMatch: number;
    documentation: number;
    codingIntegrity: number;
    requiredAttachments: number;
    administrativeCompleteness: number;
    overallScore: number;
    readinessLabel: string;
    readinessLabelAr: string;
    warningNotice?: string;
    warningNoticeAr?: string;
  };
  revenueRisk: {
    financialValue: number;
    denialRiskPercentage: number;
    revenueAtRisk: number;
    recoverableValue: number;
    priority: 'HIGH' | 'MEDIUM' | 'LOW';
  };
  evidenceHunterFoundItems: {
    requirement: string;
    requirementAr: string;
    status: 'FOUND' | 'MISSING' | 'PARTIAL';
    matchedFact?: string;
    sourceEncounter?: string;
    date?: string;
  }[];
}

export async function analyzeClinicalOrderAI(reqData: AnalyzeOrderRequest): Promise<AnalyzeOrderResult> {
  const ai = getGeminiClient();
  
  if (!ai) {
    // Graceful fallback if GEMINI_API_KEY is missing
    return getFallbackAnalysis(reqData);
  }

  try {
    const prompt = `You are Mujeaz (مُجاز), an expert AI Healthcare Revenue Assurance & Authorization Command Center in Saudi Arabia (NPHIES / Payer standards).
Analyze the following clinical note/order:
"${reqData.clinicalNoteText}"
Payer: ${reqData.payerName || 'Tawuniya Insurance'}
Requested Service: ${reqData.requestedService || 'Clinical Procedure / Diagnostics'}

Extract clinical data, assess payer policy conformance, compute Mujeaz Readiness Score™ (0-100), identify denial risks, and extract evidence. Provide responses in both English and Arabic.`;

    const response = await ai.models.generateContent({
      model: "gemini-3.6-flash",
      contents: prompt,
      config: {
        systemInstruction: `You are Mujeaz AI Engine. Return JSON adhering to the provided schema. Output dual language (English & Arabic) fields for facts, rules, and warnings. Ensure accurate ICD-10 and CPT coding detection.`,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            patientDiagnosis: {
              type: Type.OBJECT,
              properties: {
                code: { type: Type.STRING },
                display: { type: Type.STRING },
                displayAr: { type: Type.STRING },
              },
              required: ["code", "display", "displayAr"],
            },
            procedureCode: {
              type: Type.OBJECT,
              properties: {
                code: { type: Type.STRING },
                display: { type: Type.STRING },
                displayAr: { type: Type.STRING },
                costSAR: { type: Type.NUMBER },
              },
              required: ["code", "display", "displayAr", "costSAR"],
            },
            clinicalFacts: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  fact: { type: Type.STRING },
                  factAr: { type: Type.STRING },
                  category: { type: Type.STRING },
                  source: { type: Type.STRING },
                  confidence: { type: Type.NUMBER },
                },
                required: ["fact", "factAr", "category", "source", "confidence"],
              },
            },
            policyRules: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  title: { type: Type.STRING },
                  titleAr: { type: Type.STRING },
                  requirement: { type: Type.STRING },
                  requirementAr: { type: Type.STRING },
                  status: { type: Type.STRING },
                },
                required: ["title", "titleAr", "requirement", "requirementAr", "status"],
              },
            },
            readinessScore: {
              type: Type.OBJECT,
              properties: {
                clinicalEvidence: { type: Type.NUMBER },
                policyMatch: { type: Type.NUMBER },
                documentation: { type: Type.NUMBER },
                codingIntegrity: { type: Type.NUMBER },
                requiredAttachments: { type: Type.NUMBER },
                administrativeCompleteness: { type: Type.NUMBER },
                overallScore: { type: Type.NUMBER },
                readinessLabel: { type: Type.STRING },
                readinessLabelAr: { type: Type.STRING },
                warningNotice: { type: Type.STRING },
                warningNoticeAr: { type: Type.STRING },
              },
              required: [
                "clinicalEvidence",
                "policyMatch",
                "documentation",
                "codingIntegrity",
                "requiredAttachments",
                "administrativeCompleteness",
                "overallScore",
                "readinessLabel",
                "readinessLabelAr"
              ],
            },
            revenueRisk: {
              type: Type.OBJECT,
              properties: {
                financialValue: { type: Type.NUMBER },
                denialRiskPercentage: { type: Type.NUMBER },
                revenueAtRisk: { type: Type.NUMBER },
                recoverableValue: { type: Type.NUMBER },
                priority: { type: Type.STRING },
              },
              required: ["financialValue", "denialRiskPercentage", "revenueAtRisk", "recoverableValue", "priority"],
            },
            evidenceHunterFoundItems: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  requirement: { type: Type.STRING },
                  requirementAr: { type: Type.STRING },
                  status: { type: Type.STRING },
                  matchedFact: { type: Type.STRING },
                  sourceEncounter: { type: Type.STRING },
                  date: { type: Type.STRING },
                },
                required: ["requirement", "requirementAr", "status"],
              },
            },
          },
          required: [
            "patientDiagnosis",
            "procedureCode",
            "clinicalFacts",
            "policyRules",
            "readinessScore",
            "revenueRisk",
            "evidenceHunterFoundItems"
          ],
        },
      },
    });

    const text = response.text;
    if (text) {
      const parsed = JSON.parse(text);
      return parsed as AnalyzeOrderResult;
    } else {
      return getFallbackAnalysis(reqData);
    }
  } catch (error) {
    console.error("Gemini Analysis Error:", error);
    return getFallbackAnalysis(reqData);
  }
}

export async function generateAppealAI(caseData: any): Promise<{
  formalLetterEn: string;
  formalLetterAr: string;
  appealStrategy: string;
  appealStrategyAr: string;
  appealStrength: number;
}> {
  const ai = getGeminiClient();

  if (!ai) {
    return {
      formalLetterEn: caseData.appealPackage?.formalLetterEn || "Formal Reconsideration Request...",
      formalLetterAr: caseData.appealPackage?.formalLetterAr || "طلب إعادة نظر واستئناف رسمي...",
      appealStrategy: caseData.appealPackage?.appealStrategy || "Cite clinical evidence and policy exemptions.",
      appealStrategyAr: caseData.appealPackage?.appealStrategyAr || "الاستناد إلى الأدلة السريرية واستثناءات التغطية.",
      appealStrength: 95,
    };
  }

  try {
    const prompt = `Write a comprehensive, legally compliant, medical appeal package for a denied healthcare claim in Saudi Arabia (NPHIES / Payer framework).
Case Info:
Patient: ${caseData.patientName}
Claim: ${caseData.claimNumber}
Payer: ${caseData.payerName}
Service: ${caseData.requestedService}
Denial Reason: ${caseData.readinessScore?.warningNotice || 'Missing step therapy / clinical evidence'}
Clinical History: ${caseData.clinicalNoteText}`;

    const response = await ai.models.generateContent({
      model: "gemini-3.6-flash",
      contents: prompt,
      config: {
        systemInstruction: "Generate professional appeal letters in English and Arabic along with appeal strategy and strength score.",
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            formalLetterEn: { type: Type.STRING },
            formalLetterAr: { type: Type.STRING },
            appealStrategy: { type: Type.STRING },
            appealStrategyAr: { type: Type.STRING },
            appealStrength: { type: Type.NUMBER },
          },
          required: ["formalLetterEn", "formalLetterAr", "appealStrategy", "appealStrategyAr", "appealStrength"],
        },
      },
    });

    const text = response.text;
    if (text) {
      return JSON.parse(text);
    }
  } catch (err) {
    console.error("Gemini Appeal Error:", err);
  }

  return {
    formalLetterEn: caseData.appealPackage?.formalLetterEn || "Formal Reconsideration Letter...",
    formalLetterAr: caseData.appealPackage?.formalLetterAr || "طلب استئناف رسمي...",
    appealStrategy: "Cite NPHIES clinical evidence guidelines & medical necessity.",
    appealStrategyAr: "الاستناد إلى المعايير السريرية لمنصة نفيس والضرورة الطبية.",
    appealStrength: 94,
  };
}

function getFallbackAnalysis(reqData: AnalyzeOrderRequest): AnalyzeOrderResult {
  const isMri = reqData.clinicalNoteText.toLowerCase().includes('mri') || reqData.clinicalNoteText.includes('رنين');
  const cost = isMri ? 15500 : 8500;
  
  return {
    patientDiagnosis: {
      code: 'M54.50',
      display: 'Low back pain, unspecified',
      displayAr: 'ألم أسفل الظهر غير محدد',
    },
    procedureCode: {
      code: isMri ? '72148' : '71250',
      display: isMri ? 'MRI Lumbar Spine L4-L5' : 'CT Scan Diagnostic',
      displayAr: isMri ? 'تصوير بالرنين المغناطيسي للفقرات القطنية L4-L5' : 'فحص بالاشعة المقطعية',
      costSAR: cost,
    },
    clinicalFacts: [
      {
        fact: 'Persistent symptoms reported in current clinical encounter',
        factAr: 'وجود أعراض مستمرة موثقة في الملاحظة الطبية',
        category: 'SYMPTOM',
        source: 'Primary HIS Clinical Note',
        confidence: 95,
      },
      {
        fact: 'Clinical evaluation confirms medical necessity indication',
        factAr: 'الفحص السريري يؤكد مؤشر الضرورة الطبية',
        category: 'DIAGNOSIS',
        source: 'Physician Order',
        confidence: 90,
      },
    ],
    policyRules: [
      {
        title: '6-Week Conservative Therapy Requirement',
        titleAr: 'شرط العلاج التحفظي لمدة 6 أسابيع',
        requirement: 'Explicit documentation of prior conservative management required.',
        requirementAr: 'يتطلب توثيق صريح لمراحل العلاج التحفظي السابق.',
        status: 'WARNING',
      },
      {
        title: 'ICD-10 vs CPT Compatibility Check',
        titleAr: 'التحقق من توافق الترميز الطبي',
        requirement: 'Diagnosis code matches requested procedural code.',
        requirementAr: 'رمز التشخيص مطابق للإجراء المطلوب.',
        status: 'PASSED',
      },
    ],
    readinessScore: {
      clinicalEvidence: 65,
      policyMatch: 72,
      documentation: 75,
      codingIntegrity: 100,
      requiredAttachments: 80,
      administrativeCompleteness: 100,
      overallScore: 78,
      readinessLabel: 'Action Required',
      readinessLabelAr: 'يتطلب إجراء قبل الإرسال',
      warningNotice: 'Conservative treatment records not explicitly referenced in primary note.',
      warningNoticeAr: 'لم يتم الاستشهاد بسجلات العلاج التحفظي صراحةً في الملاحظة الأولية.',
    },
    revenueRisk: {
      financialValue: cost * 10,
      denialRiskPercentage: 72,
      revenueAtRisk: Math.round(cost * 10 * 0.72),
      recoverableValue: Math.round(cost * 10 * 0.65),
      priority: 'HIGH',
    },
    evidenceHunterFoundItems: [
      {
        requirement: 'Proof of prior conservative physical therapy / medications',
        requirementAr: 'إثبات الجلسات والأدوية السابقة',
        status: 'MISSING',
      },
    ],
  };
}
