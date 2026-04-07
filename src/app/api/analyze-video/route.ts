import { NextRequest, NextResponse } from 'next/server';

export const maxDuration = 60;

const GEMINI_API_URL =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

function buildPrompt(customPrompt?: string): string {
  const extra = customPrompt
    ? `\n\nДОПОЛНИТЕЛЬНЫЕ ИНСТРУКЦИИ ОТ ПОЛЬЗОВАТЕЛЯ: ${customPrompt}`
    : '';
  return `Ты профессиональный SMM-менеджер. Проанализируй видео и дай ответ СТРОГО в JSON без markdown:\n{\n  "description": "Детальное описание 3-5 предложений на русском",\n  "threadPost": "Готовый пост для Threads с эмодзи на русском",\n  "hashtags": ["хэштег1", "хэштег2"],\n  "mood": "позитивный",\n  "topics": ["тема1", "тема2"],\n  "engagementScore": 75\n}\nТребования: description подробное, threadPost живой, hashtags 5-10 без #, mood одно из: позитивный/вдохновляющий/развлекательный/информационный/эмоциональный/спокойный, engagementScore 0-100${extra}\nВерни ТОЛЬКО JSON.`;
}

async function callGemini(apiKey: string, parts: object[]): Promise<string> {
  const res = await fetch(`${GEMINI_API_URL}?key=${apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents: [{ parts }], generationConfig: { temperature: 0.7, maxOutputTokens: 2048 } }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = (err as { error?: { message?: string } })?.error?.message || `HTTP ${res.status}`;
    throw new Error(`Gemini API error: ${msg}`);
  }
  const data = (await res.json()) as { candidates?: { content?: { parts?: { text?: string }[] } }[] };
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error('Gemini returned empty response');
  return text.trim();
}

function parseGeminiJSON(raw: string) {
  const cleaned = raw.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/i, '').trim();
  try { return JSON.parse(cleaned); } catch {
    const match = cleaned.match(/\{[\s\S]*\}/);
    if (!match) throw new Error('Unexpected AI format');
    return JSON.parse(match[0]);
  }
}

export async function POST(req: NextRequest) {
  try {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) return NextResponse.json({ error: 'GEMINI_API_KEY not set' }, { status: 500 });
    const formData = await req.formData();
    const url = formData.get('url') as string | null;
    const file = formData.get('file') as File | null;
    const customPrompt = formData.get('customPrompt') as string | null;
    if (!url && !file) return NextResponse.json({ error: 'Provide URL or file' }, { status: 400 });
    const prompt = buildPrompt(customPrompt || undefined);
    let rawText: string;
    if (file) {
      const bytes = await file.arrayBuffer();
      const base64 = Buffer.from(bytes).toString('base64');
      rawText = await callGemini(apiKey, [{ text: prompt }, { inlineData: { mimeType: file.type || 'video/mp4', data: base64 } }]);
    } else {
      let fetched = false;
      try {
        const vr = await fetch(url!, { headers: { 'User-Agent': 'Mozilla/5.0' }, signal: AbortSignal.timeout(15000) });
        const ct = vr.headers.get('content-type') || '';
        if (vr.ok && (ct.startsWith('video/') || ct.includes('octet-stream'))) {
          const buf = await vr.arrayBuffer();
          rawText = await callGemini(apiKey, [{ text: prompt }, { inlineData: { mimeType: ct.split(';')[0], data: Buffer.from(buf).toString('base64') } }]);
          fetched = true;
        }
      } catch {}
      if (!fetched) {
        rawText = await callGemini(apiKey, [{ text: `${prompt}\n\nURL для анализа: ${url}\nАнализ основан на URL.` }]);
      }
    }
    const parsed = parseGeminiJSON(rawText);
    return NextResponse.json({
      description: String(parsed.description || '').trim(),
      threadPost: String(parsed.threadPost || '').trim(),
      hashtags: Array.isArray(parsed.hashtags) ? parsed.hashtags.map((h: unknown) => String(h).replace(/^#/, '').trim()).filter(Boolean) : [],
      mood: String(parsed.mood || 'позитивный').trim().toLowerCase(),
      topics: Array.isArray(parsed.topics) ? parsed.topics.map((t: unknown) => String(t).trim()).filter(Boolean) : [],
      engagementScore: Math.min(100, Math.max(0, Number(parsed.engagementScore) || 75)),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Server error';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
