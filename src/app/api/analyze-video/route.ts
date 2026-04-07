import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60;

const GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent";

async function callGemini(apiKey: string, parts: object[]): Promise<string> {
  const res = await fetch(GEMINI_API_URL + "?key=" + apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts }],
      generationConfig: { temperature: 0.7, maxOutputTokens: 2048 },
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = (err as { error?: { message?: string } })?.error?.message || "HTTP " + res.status;
    throw new Error("Gemini API error: " + msg);
  }
  const data = await res.json() as { candidates?: { content?: { parts?: { text?: string }[] } }[] };
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error("Gemini returned empty response");
  return text.trim();
}

function parseJSON(raw: string) {
  const cleaned = raw.replace(/^`{3}(?:json)?\n?/i, "").replace(/\n?`{3}$/i, "").trim();
  try { return JSON.parse(cleaned); } catch {
    const match = cleaned.match(/\{[\s\S]*\}/);
    if (!match) throw new Error("Unexpected AI response format");
    return JSON.parse(match[0]);
  }
}

export async function POST(req: NextRequest) {
  try {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });

    const contentType = req.headers.get("content-type") || "";
    let videoUrl: string | null = null;
    let videoFile: File | null = null;

    if (contentType.includes("application/json")) {
      const body = await req.json() as { videoUrl?: string };
      videoUrl = body.videoUrl || null;
    } else {
      const form = await req.formData();
      videoUrl = form.get("url") as string | null;
      videoFile = form.get("video") as File | null;
      if (!videoFile) videoFile = form.get("file") as File | null;
    }

    if (!videoUrl && !videoFile) return NextResponse.json({ error: "Provide URL or upload file" }, { status: 400 });

    const prompt = `You are an expert social media manager and content analyst.
Analyze this video and return ONLY valid JSON (no markdown):
{
  "description": "Detailed English description of the video, 3-5 sentences covering people, actions, setting, atmosphere, key moments.",
  "threadPost": "An engaging ready-to-post Threads caption in English. Conversational, emotional, with call to action. 2-3 paragraphs. Use relevant emojis.",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
  "contentType": "One of: education, entertainment, lifestyle, technology, sports, music, news, humor",
  "mood": "One of: positive, inspiring, entertaining, informative, emotional, calm",
  "suggestedTime": "Best time to post, e.g. 7:00 PM EST",
  "engagementScore": 75
}
Requirements: hashtags: 5-10 relevant tags WITHOUT # symbol, engagementScore: 0-100`;

    let rawText = "";

    if (videoFile) {
      const bytes = await videoFile.arrayBuffer();
      const base64 = Buffer.from(bytes).toString("base64");
      rawText = await callGemini(apiKey, [{ text: prompt }, { inlineData: { mimeType: videoFile.type || "video/mp4", data: base64 } }]);
    } else if (videoUrl) {
      let fetched = false;
      try {
        const vres = await fetch(videoUrl, { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(15000) });
        const ct = vres.headers.get("content-type") || "";
        if (vres.ok && (ct.startsWith("video/") || ct.includes("octet-stream"))) {
          const buf = await vres.arrayBuffer();
          rawText = await callGemini(apiKey, [{ text: prompt }, { inlineData: { mimeType: ct.split(";")[0], data: Buffer.from(buf).toString("base64") } }]);
          fetched = true;
        }
      } catch { /* ignore */ }
      if (!fetched) {
        rawText = await callGemini(apiKey, [{ text: prompt + "\n\nVIDEO URL (analyze context): " + videoUrl }]);
      }
    }

    if (!rawText) return NextResponse.json({ error: "Could not analyze video" }, { status: 422 });

    const parsed = parseJSON(rawText);

    return NextResponse.json({
      description: String(parsed.description || "").trim(),
      threadPost: String(parsed.threadPost || "").trim(),
      hashtags: Array.isArray(parsed.hashtags) ? parsed.hashtags.map((h: unknown) => String(h).replace(/^#/, "").trim()).filter(Boolean) : [],
      contentType: String(parsed.contentType || "entertainment"),
      mood: String(parsed.mood || "positive"),
      suggestedTime: String(parsed.suggestedTime || "7:00 PM"),
      engagementScore: Math.min(100, Math.max(0, Number(parsed.engagementScore) || 75)),
    });
  } catch (err: unknown) {
    console.error("[analyze-video]", err);
    return NextResponse.json({ error: err instanceof Error ? err.message : "Internal server error" }, { status: 500 });
  }
      }
