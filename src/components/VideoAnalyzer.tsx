'use client';
import React, { useState, useCallback, useRef } from 'react';
import { Wand2, Upload, Link, Loader2, CheckCircle2, AlertCircle, Copy, Sparkles, Hash, MessageSquare, TrendingUp, Video, X, Play } from 'lucide-react';

interface VideoAnalysisResult {
  description: string;
  threadPost: string;
  hashtags: string[];
  engagementScore: number;
  contentType: string;
  mood: string;
  suggestedTime: string;
}

export default function VideoAnalyzer() {
  const [mode, setMode] = useState<'url' | 'file'>('url');
  const [videoUrl, setVideoUrl] = useState('');
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VideoAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith('video/')) { setError('Please select a video file'); return; }
    if (file.size > 100 * 1024 * 1024) { setError('File too large. Max 100MB'); return; }
    setVideoFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setError(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const analyze = async () => {
    if (mode === 'url' && !videoUrl) { setError('Enter a video URL'); return; }
    if (mode === 'file' && !videoFile) { setError('Select a video file'); return; }
    setLoading(true); setError(null); setResult(null);
    try {
      let body: FormData | string;
      let headers: Record<string, string> = {};
      if (mode === 'file' && videoFile) {
        const fd = new FormData();
        fd.append('video', videoFile);
        body = fd;
      } else {
        body = JSON.stringify({ videoUrl });
        headers['Content-Type'] = 'application/json';
      }
      const res = await fetch('/api/analyze-video', { method: 'POST', headers, body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Analysis failed');
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const copy = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const reset = () => {
    setVideoUrl(''); setVideoFile(null); setPreviewUrl(null);
    setResult(null); setError(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #8b5cf6, #e1306c)' }}>
          <Wand2 size={24} className="text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">AI Video Analysis <span className="text-xs px-2 py-0.5 rounded-full font-bold" style={{ background: 'linear-gradient(135deg, #8b5cf6, #e1306c)', color: 'white' }}>AI</span></h2>
          <p className="text-slate-400 text-sm">Analyze video with Google Gemini AI and generate Threads content</p>
        </div>
      </div>

      {/* Mode Tabs */}
      <div className="glass-card p-6">
        <div className="flex gap-2 mb-6">
          {[{ id: 'url', icon: <Link size={16} />, label: 'Video URL' }, { id: 'file', icon: <Upload size={16} />, label: 'Upload File' }].map(m => (
            <button key={m.id} onClick={() => { setMode(m.id as 'url' | 'file'); reset(); }} className={'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ' + (mode === m.id ? 'text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10')} style={mode === m.id ? { background: 'linear-gradient(135deg, #8b5cf6, #e1306c)' } : {}}>
              {m.icon} {m.label}
            </button>
          ))}
        </div>

        {mode === 'url' ? (
          <div>
            <label className="text-sm text-slate-400 mb-2 block">Video URL (YouTube, TikTok, etc.)</label>
            <div className="flex gap-3">
              <input type="url" value={videoUrl} onChange={e => setVideoUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." className="glass-input flex-1" onKeyDown={e => e.key === 'Enter' && analyze()} />
              <button onClick={analyze} disabled={loading || !videoUrl} className="px-6 py-3 rounded-xl font-medium text-white text-sm flex items-center gap-2 disabled:opacity-40 transition-all" style={{ background: 'linear-gradient(135deg, #8b5cf6, #e1306c)', boxShadow: '0 4px 15px rgba(139,92,246,0.3)' }}>
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>
          </div>
        ) : (
          <div>
            {!videoFile ? (
              <div onDragOver={e => { e.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onDrop={handleDrop} onClick={() => fileRef.current?.click()} className={'border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ' + (isDragging ? 'border-purple-500 bg-purple-500/10' : 'border-slate-700 hover:border-purple-500/50 hover:bg-purple-500/5')}>
                <input ref={fileRef} type="file" accept="video/*" onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} className="hidden" />
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(225,48,108,0.2))' }}><Upload size={28} className="text-purple-400" /></div>
                <p className="text-lg font-medium mb-1">Drop video here</p>
                <p className="text-sm text-slate-500">MP4, MOV, AVI — max 100MB</p>
              </div>
            ) : (
              <div>
                <div className="relative rounded-2xl overflow-hidden mb-4" style={{ background: 'rgba(15,23,42,0.8)' }}>
                  {previewUrl && <video src={previewUrl} controls className="w-full max-h-64 object-contain" />}
                  <button onClick={reset} className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/60 flex items-center justify-center hover:bg-black/80 transition-colors"><X size={16} /></button>
                </div>
                <div className="flex items-center justify-between">
                  <div><p className="text-sm font-medium">{videoFile.name}</p><p className="text-xs text-slate-400">{(videoFile.size / 1024 / 1024).toFixed(2)} MB</p></div>
                  <button onClick={analyze} disabled={loading} className="px-6 py-3 rounded-xl font-medium text-white text-sm flex items-center gap-2 disabled:opacity-40" style={{ background: 'linear-gradient(135deg, #8b5cf6, #e1306c)', boxShadow: '0 4px 15px rgba(139,92,246,0.3)' }}>
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                    {loading ? 'Analyzing...' : 'Analyze with AI'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 rounded-xl flex items-center gap-3" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <AlertCircle size={18} className="text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {loading && (
          <div className="mt-6 p-6 rounded-2xl text-center" style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.08), rgba(225,48,108,0.08))', border: '1px solid rgba(139,92,246,0.2)' }}>
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(225,48,108,0.2))' }}><Wand2 size={24} className="text-purple-400 animate-pulse" /></div>
            <p className="font-medium mb-1">Analyzing with Google Gemini AI...</p>
            <p className="text-sm text-slate-400">This may take a few seconds</p>
            <div className="flex justify-center gap-1.5 mt-4">{[0,1,2].map(i => <div key={i} className="w-2 h-2 rounded-full bg-purple-400" style={{ animation: 'pulse 1.4s ease-in-out ' + (i * 0.2) + 's infinite' }} />)}</div>
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-4">
          {/* Success Banner */}
          <div className="glass-card p-4 flex items-center gap-3" style={{ background: 'rgba(16,185,129,0.05)', borderColor: 'rgba(16,185,129,0.2)' }}>
            <CheckCircle2 size={20} className="text-emerald-400 flex-shrink-0" />
            <div className="flex-1"><p className="text-sm font-medium text-emerald-400">Analysis complete!</p><p className="text-xs text-slate-400">Content: {result.contentType} | Mood: {result.mood} | Best post time: {result.suggestedTime}</p></div>
            <div className="px-3 py-1 rounded-full text-sm font-bold" style={{ background: result.engagementScore >= 80 ? 'rgba(16,185,129,0.2)' : result.engagementScore >= 60 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)', color: result.engagementScore >= 80 ? '#34d399' : result.engagementScore >= 60 ? '#fbbf24' : '#f87171' }}>
              {result.engagementScore}/100
            </div>
          </div>

          {/* Description */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold flex items-center gap-2"><Video size={18} className="text-blue-400" />Video Description</h3>
              <button onClick={() => copy(result.description, 'desc')} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-blue-400 transition-colors">{copied === 'desc' ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}{copied === 'desc' ? 'Copied!' : 'Copy'}</button>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{result.description}</p>
          </div>

          {/* Thread Post */}
          <div className="glass-card p-6" style={{ borderColor: 'rgba(139,92,246,0.2)' }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold flex items-center gap-2"><MessageSquare size={18} className="text-purple-400" />Ready-to-Post Thread</h3>
              <button onClick={() => copy(result.threadPost, 'post')} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-purple-400 transition-colors">{copied === 'post' ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}{copied === 'post' ? 'Copied!' : 'Copy'}</button>
            </div>
            <div className="p-4 rounded-xl text-sm text-slate-200 leading-relaxed whitespace-pre-wrap" style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.15)' }}>{result.threadPost}</div>
          </div>

          {/* Hashtags */}
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold flex items-center gap-2"><Hash size={18} className="text-emerald-400" />Recommended Hashtags</h3>
              <button onClick={() => copy(result.hashtags.join(' '), 'tags')} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-emerald-400 transition-colors">{copied === 'tags' ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}{copied === 'tags' ? 'Copied!' : 'Copy All'}</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.hashtags.map((tag, i) => (
                <button key={i} onClick={() => copy(tag, 'tag_' + i)} className="px-3 py-1.5 rounded-full text-sm font-medium transition-all hover:scale-105" style={{ background: 'rgba(16,185,129,0.1)', color: '#34d399', border: '1px solid rgba(16,185,129,0.2)' }}>{tag}</button>
              ))}
            </div>
          </div>

          {/* Engagement Score */}
          <div className="glass-card p-6">
            <h3 className="font-semibold flex items-center gap-2 mb-4"><TrendingUp size={18} className="text-amber-400" />Predicted Engagement</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="progress-bar h-3"><div className="progress-bar-fill h-3 transition-all duration-1000" style={{ width: result.engagementScore + '%', background: result.engagementScore >= 80 ? 'var(--gradient-success)' : result.engagementScore >= 60 ? 'var(--gradient-warning)' : 'var(--gradient-danger)' }} /></div>
              </div>
              <span className="text-2xl font-bold" style={{ color: result.engagementScore >= 80 ? '#34d399' : result.engagementScore >= 60 ? '#fbbf24' : '#f87171' }}>{result.engagementScore}%</span>
            </div>
            <p className="text-xs text-slate-400 mt-2">{result.engagementScore >= 80 ? 'Excellent potential! This content is likely to go viral.' : result.engagementScore >= 60 ? 'Good potential. With the right timing, this will perform well.' : 'Consider improving video quality and content for better engagement.'}</p>
          </div>
        </div>
      )}
    </div>
  );
    }
