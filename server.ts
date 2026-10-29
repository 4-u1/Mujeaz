import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { analyzeClinicalOrderAI, generateAppealAI } from './server/geminiService.js';

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '10mb' }));

  // API Routes
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', service: 'Mujeaz AI Engine', timestamp: new Date().toISOString() });
  });

  // Analyze Clinical Order with Gemini AI
  app.post('/api/ai/analyze-order', async (req, res) => {
    try {
      const { clinicalNoteText, payerName, requestedService } = req.body;
      if (!clinicalNoteText) {
        return res.status(400).json({ error: 'clinicalNoteText is required' });
      }
      const result = await analyzeClinicalOrderAI({ clinicalNoteText, payerName, requestedService });
      res.json(result);
    } catch (err: any) {
      console.error('Error analyzing order:', err);
      res.status(500).json({ error: 'Failed to analyze clinical order', details: err.message });
    }
  });

  // Trigger A6 Recovery Agent for Appeals
  app.post('/api/ai/generate-appeal', async (req, res) => {
    try {
      const caseData = req.body;
      const result = await generateAppealAI(caseData);
      res.json(result);
    } catch (err: any) {
      console.error('Error generating appeal:', err);
      res.status(500).json({ error: 'Failed to generate appeal', details: err.message });
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
