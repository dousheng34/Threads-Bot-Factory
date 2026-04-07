const THREADS_API_BASE = 'https://graph.threads.net/v1.0';

export interface ThreadsApiConfig { accessToken: string; userId: string; proxyUrl?: string; }
export interface PublishResult { success: boolean; threadId?: string; error?: string; }

export async function exchangeCodeForToken(code: string, appId: string, appSecret: string, redirectUri: string): Promise<{ accessToken: string; userId: string }> {
  const response = await fetch(`${THREADS_API_BASE}/oauth/access_token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_id: appId, client_secret: appSecret, grant_type: 'authorization_code', redirect_uri: redirectUri, code }) });
  const data = await response.json();
  if (data.error) throw new Error(data.error.message);
  return { accessToken: data.access_token, userId: data.user_id };
}

export async function publishThread(config: ThreadsApiConfig, text: string, options?: { imageUrl?: string; videoUrl?: string; replyToId?: string; }): Promise<PublishResult> {
  try {
    const body: Record<string, string> = { media_type: 'TEXT', text, access_token: config.accessToken };
    if (options?.replyToId) body.reply_to_id = options.replyToId;
    const r1 = await fetch(`${THREADS_API_BASE}/${config.userId}/threads`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(body) });
    const d1 = await r1.json();
    if (d1.error) throw new Error(d1.error.message);
    const containerId = d1.id;
    await new Promise(resolve => setTimeout(resolve, 5000));
    const r2 = await fetch(`${THREADS_API_BASE}/${config.userId}/threads_publish`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ creation_id: containerId, access_token: config.accessToken }) });
    const d2 = await r2.json();
    if (d2.error) throw new Error(d2.error.message);
    return { success: true, threadId: d2.id };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export function processSpintax(text: string): string {
  const regex = /\{([^{}]+)\}/g;
  return text.replace(regex, (_, options: string) => { const choices = options.split('|'); return choices[Math.floor(Math.random() * choices.length)]; });
}

export async function getUserProfile(config: ThreadsApiConfig) {
  const params = new URLSearchParams({ fields: 'id,username,threads_profile_picture_url,threads_biography', access_token: config.accessToken });
  const r = await fetch(`${THREADS_API_BASE}/${config.userId}?${params}`);
  const data = await r.json();
  if (data.error) throw new Error(data.error.message);
  return data;
}

export async function getPublishingLimit(config: ThreadsApiConfig) {
  const params = new URLSearchParams({ fields: 'quota_usage,config', access_token: config.accessToken });
  const r = await fetch(`${THREADS_API_BASE}/${config.userId}/threads_publishing_limit?${params}`);
  const data = await r.json();
  if (data.error) throw new Error(data.error.message);
  return data;
}
