import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { analyzeClinicalOrderAI, generateAppealAI } from './server/geminiService.js';

const MAX_NOTE_CHARS = 20000;
const MAX_FIELD_CHARS = 500;

/** Minimal in-memory rate limiter for the AI endpoints (per IP, fixed window). */
function rateLimit(maxRequests: number, windowMs: number): express.RequestHandler {
  const hits = new Map<string, { count: number; resetAt: number }>();
  return (req, res, next) => {
    const key = req.ip || 'unknown';
    const now = Date.now();
    const entry = hits.get(key);
    if (!entry || entry.resetAt < now) {
      hits.set(key, { count: 1, resetAt: now + windowMs });
      return next();
    }
    if (entry.count >= maxRequests) {
      res.setHeader('Retry-After', Math.ceil((entry.resetAt - now) / 1000));
      return res.status(429).json({ error: 'Too many requests. Please try again shortly.' });
    }
    entry.count += 1;
    next();
  };
}

const isOptionalString = (v: unknown, max: number) => v === undefined || (typeof v === 'string' && v.length <= max);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '200kb' }));
  const aiLimiter = rateLimit(20, 60_000);

  // API Routes
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'Mujeaz AI Engine', timestamp: new Date().toISOString() });
  });

  // Analyze Clinical Order with Gemini AI
  app.post('/api/ai/analyze-order', aiLimiter, async (req, res) => {
    try {
      const { clinicalNoteText, payerName, requestedService } = req.body ?? {};
      if (typeof clinicalNoteText !== 'string' || !clinicalNoteText.trim()) {
        return res.status(400).json({ error: 'clinicalNoteText is required' });
      }
      if (clinicalNoteText.length > MAX_NOTE_CHARS) {
        return res.status(413).json({ error: `clinicalNoteText exceeds ${MAX_NOTE_CHARS} characters` });
      }
      if (!isOptionalString(payerName, MAX_FIELD_CHARS) || !isOptionalString(requestedService, MAX_FIELD_CHARS)) {
        return res.status(400).json({ error: 'payerName and requestedService must be short strings' });
      }
      const result = await analyzeClinicalOrderAI({ clinicalNoteText, payerName, requestedService });
      res.json(result);
    } catch (err: any) {
      console.error('Error analyzing order:', err);
      res.status(500).json({ error: 'Failed to analyze clinical order' });
    }
  });

  // Trigger A6 Recovery Agent for Appeals
  app.post('/api/ai/generate-appeal', aiLimiter, async (req, res) => {
    try {
      const b = req.body ?? {};
      const shortFields = ['claimNumber', 'payerName', 'requestedService', 'denialReason'];
      if (shortFields.some((k) => !isOptionalString(b[k], MAX_FIELD_CHARS)) || !isOptionalString(b.clinicalNoteText, MAX_NOTE_CHARS)) {
        return res.status(400).json({ error: 'Invalid appeal request fields' });
      }
      const evidence = Array.isArray(b.evidence)
        ? b.evidence
            .slice(0, 50)
            .filter((e: any) => e && typeof e.fact === 'string' && typeof e.source === 'string')
            .map((e: any) => ({ fact: e.fact.slice(0, 1000), source: e.source.slice(0, 300), date: typeof e.date === 'string' ? e.date.slice(0, 30) : undefined }))
        : undefined;
      // Only whitelisted fields reach the model (data minimisation): no patient name or ID.
      const result = await generateAppealAI({
        claimNumber: b.claimNumber,
        payerName: b.payerName,
        requestedService: b.requestedService,
        denialReason: b.denialReason,
        clinicalNoteText: b.clinicalNoteText,
        evidence,
        appealPackage: b.appealPackage && typeof b.appealPackage === 'object' ? b.appealPackage : undefined,
      });
      res.json(result);
    } catch (err: any) {
      console.error('Error generating appeal:', err);
      res.status(500).json({ error: 'Failed to generate appeal' });
    }
  });

  // Vite middleware for dev or Static files for prod
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Mujeaz Command Center] Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
