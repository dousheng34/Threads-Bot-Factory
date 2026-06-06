import { NextRequest, NextResponse } from 'next/server';

export const maxDuration = 60;

const GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

async function callGemini(apiKey: string, parts: any[]) {
    const res = await fetch(GEMINI_URL + '?key=' + apiKey, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ contents: [{ parts }], generationConfig: { temperature: 0.7, maxOutputTokens: 2048 } }),
    });
    if (!res.ok) {
          const e = await res.json().catch(() => ({}));
          throw new Error('Gemini error: ' + (e?.error?.message || res.status));
    }
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error('Gemini returned empty response');
    return text.trim();
}

function parseJSON(raw: string) {
    const cleaned = raw.replace(/^\`\`\`(?:json)?\n?/i, '').replace(/\n?\`\`\`$/i, '').trim();
    try { return JSON.parse(cleaned); } catch {
          const m = cleaned.match(/{[\s\S]*}/);
          if (!m) throw new Error('Unexpected AI response format');
          return JSON.parse(m[0]);
    }
}

export async function POST(req: Request) {
    try {
          const apiKey = process.env.GEMINI_API_KEY;
          if (!apiKey) return NextResponse.json({ error: 'GEMINI_API_KEY not configured' }, { status: 500 });

      const ct = req.headers.get('content-type') || '';
          let videoUrl = null;
          let videoFile = null;

      if (ct.includes('application/json')) {
              const body = await req.json();
              videoUrl = body.videoUrl || null;
      } else {
              const form = await req.formData();
              videoUrl = form.get('url');
              videoFile = form.get('video') || form.get('file');
      }

      if (!videoUrl && !videoFile) {
              return NextResponse.json({ error: 'Provide URL or upload file' }, { status: 400 });
      }

      const prompt = `You are an expert social media manager. Analyze this video and return ONLY valid JSON:
      {
        "description": "Detailed description 3-5 sentences",
          "threadPost": "Engaging Threads post with emojis 2-3 paragraphs",
            "hashtags": ["tag1", "tag2"],
              "contentType": "entertainment",
                "mood": "positive",
                  "suggestedTime": "7:00 PM EST",
                    "engagementScore": 75
                    }
                    Rules: hashtags WITHOUT # symbol, 5-10 tags, engagementScore 0-100`;

      let rawText = '';

      if (videoFile && typeof videoFile !== 'string') {
              const bytes = await (videoFile as File).arrayBuffer();
              const b64 = Buffer.from(bytes).toString('base64');
              rawText = await callGemini(apiKey, [{ text: prompt }, { inlineData: { mimeType: (videoFile as File).type || 'video/mp4', data: b64 } }]);
      } else if (videoUrl) {
              let fetched = false;
              try {
                        const vres = await fetch(videoUrl, { headers: { 'User-Agent': 'Mozilla/5.0' }, signal: AbortSignal.timeout(15000) });
                        const vct = vres.headers.get('content-type') || '';
                        if (vres.ok && (vct.startsWith('video/') || vct.includes('octet-stream'))) {
                                    const buf = await vres.arrayBuffer();
                                    rawText = await callGemini(apiKey, [{ text: prompt }, { inlineData: { mimeType: vct.split(';')[0], data: Buffer.from(buf).toString('base64') } }]);
                                    fetched = true;
                        }
              } catch { /* ignore */ }
              if (!fetched) {
                        rawText = await callGemini(apiKey, [{ text: prompt + '\n\nVIDEO URL: ' + videoUrl }]);
              }
      }

      if (!rawText) return NextResponse.json({ error: 'Analysis failed' }, { status: 422 });

      const parsed = parseJSON(rawText);
      return NextResponse.json({
          description: String(parsed.description || '').trim(),
          threadPost: String(parsed.threadPost || '').trim(),
          hashtags: Array.isArray(parsed.hashtags) ? parsed.hashtags.map(String) : [],
          contentType: String(parsed.contentType || '').trim(),
          mood: String(parsed.mood || '').trim(),
          suggestedTime: String(parsed.suggestedTime || '').trim(),
          engagementScore: Number(parsed.engagementScore || 0)
      });
  } catch (error: any) {
      return NextResponse.json({ error: error.message || 'Server error' }, { status: 500 });
  }
}
