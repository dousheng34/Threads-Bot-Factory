'use client';
import React, { useState, useEffect } from 'react';
import { useStore } from '@/lib/store';
import { Send, Clock, Plus, Trash2, Calendar, CheckCircle2, XCircle, Loader2, Sparkles, Instagram, MessageCircle, Layers, X } from 'lucide-react';
import type { ScheduledPost } from '@/lib/types';

export default function PostScheduler() {
  const { accounts, scheduledPosts, addScheduledPost, removeScheduledPost, fetchAccounts } = useStore();
  const [show, setShow] = useState(false);
  const [originalText, setOriginalText] = useState('');
  const [selectedAccounts, setSelectedAccounts] = useState<string[]>([]);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');
  
  // AI Adaptation state
  const [isAdapting, setIsAdapting] = useState(false);
  const [activeTab, setActiveTab] = useState<'threads' | 'instagram' | 'whatsapp'>('threads');
  
  // Adapted content state
  const [threadsPosts, setThreadsPosts] = useState<string[]>(['']);
  const [igCaption, setIgCaption] = useState('');
  const [igTags, setIgTags] = useState<string[]>([]);
  const [waText, setWaText] = useState('');
  const [waCTA, setWaCTA] = useState('');

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const active = accounts.filter(a => a.status === 'active');

  const handleTransformAI = async () => {
    if (!originalText.trim()) return;
    setIsAdapting(true);
    try {
      const r = await fetch('/api/post/adapt', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ content: originalText })
      });
      if (r.ok) {
        const data = await r.json();
        const adapted = data.adapted;
        setThreadsPosts(adapted.threads || [originalText]);
        setIgCaption(adapted.instagram?.caption || originalText);
        setIgTags(adapted.instagram?.hashtags || []);
        setWaText(adapted.whatsapp?.text || originalText);
        setWaCTA(adapted.whatsapp?.cta || '');
      } else {
        alert("Ошибка сети при обращении к ИИ");
      }
    } catch (e) {
      alert("Не удалось связаться с ИИ");
    } finally {
      setIsAdapting(false);
    }
  };

  const handleCreate = async () => {
    if (selectedAccounts.length === 0) {
      alert("Выберите хотя бы один аккаунт!");
      return;
    }

    const payloadContent = {
      threads: threadsPosts.filter(Boolean),
      instagram: {
        caption: igCaption,
        hashtags: igTags
      },
      whatsapp: {
        text: waText,
        cta: waCTA
      }
    };

    const isScheduling = scheduleDate && scheduleTime;
    const targetUrl = isScheduling ? '/api/post/schedule' : '/api/post/quick';
    const postBody = {
      account_ids: selectedAccounts.map(id => Number(id.replace('acc_', ''))),
      content: payloadContent,
      media_url: mediaUrl || null,
      scheduled_at: isScheduling ? new Date(scheduleDate + 'T' + scheduleTime + ':00').toISOString() : new Date().toISOString()
    };

    try {
      const r = await fetch(targetUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(postBody)
      });
      if (r.ok) {
        alert(isScheduling ? "✅ Пост запланирован в очередь!" : "✅ Пост успешно опубликован!");
        setShow(false);
        setOriginalText('');
        setSelectedAccounts([]);
        setScheduleDate('');
        setScheduleTime('');
        setMediaUrl('');
        setThreadsPosts(['']);
        setIgCaption('');
        setIgTags([]);
        setWaText('');
        setWaCTA('');
      } else {
        const err = await r.json();
        alert(`❌ Ошибка: ${err.detail || 'Не удалось отправить пост'}`);
      }
    } catch(e) {
      alert("Ошибка сети");
    }
  };

  const addThreadPart = () => setThreadsPosts(prev => [...prev, '']);
  const removeThreadPart = (index: number) => setThreadsPosts(prev => prev.filter((_, i) => i !== index));
  const updateThreadPart = (index: number, val: string) => setThreadsPosts(prev => prev.map((item, i) => i === index ? val : item));

  const toggleAccount = (id: string) => setSelectedAccounts(prev => prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]);

  const getStatusIcon = (s: string) => { 
    switch(s) { 
      case 'published': return <CheckCircle2 size={16} className="text-emerald-400" />; 
      case 'failed': return <XCircle size={16} className="text-rose-400" />; 
      case 'publishing': return <Loader2 size={16} className="text-indigo-400 animate-spin" />; 
      default: return <Clock size={16} className="text-amber-400" />; 
    } 
  };

  return (
    <div className="space-y-6 text-slate-100 font-sans">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Публикация</h2>
          <p className="text-slate-400 text-sm mt-1">Создавайте посты, планируйте очереди и адаптируйте контент с помощью ИИ</p>
        </div>
        <button 
          onClick={() => setShow(true)} 
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all duration-200 shadow-md shadow-indigo-900/20 flex items-center gap-2"
        >
          <Plus size={16} /> Создать пост
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[{l:'В очереди',v:scheduledPosts.filter(p=>p.status==='pending').length},{l:'Опубликовано',v:scheduledPosts.filter(p=>p.status==='published').length},{l:'Ошибки',v:scheduledPosts.filter(p=>p.status==='failed').length},{l:'Всего',v:scheduledPosts.length}].map((s,i) => (
          <div key={i} className="bg-slate-950/40 border border-slate-900 rounded-xl p-4">
            <p className="text-2xl font-bold font-mono text-indigo-400">{s.v}</p>
            <p className="text-xs text-slate-400 font-medium mt-1">{s.l}</p>
          </div>
        ))}
      </div>

      {/* Scheduled Queue */}
      <div className="bg-slate-950/40 border border-slate-900 rounded-2xl overflow-hidden backdrop-blur-md">
        <div className="p-4 border-b border-slate-900"><h3 className="font-bold text-sm uppercase tracking-wider text-slate-400">Очередь постов</h3></div>
        {scheduledPosts.length === 0 ? (
          <div className="p-16 text-center text-slate-500">
            <Send size={48} className="mx-auto mb-4 opacity-30" />
            <p className="text-sm font-medium">Очередь пуста</p>
            <p className="text-xs text-slate-600 mt-1">Создайте новый пост, чтобы запланировать его.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-900/50">
            {scheduledPosts.map(post => (
              <div key={post.id} className="p-4 hover:bg-slate-900/10 flex items-start gap-4 transition-colors">
                <div className="mt-1">{getStatusIcon(post.status)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 mb-1 line-clamp-2">{post.content?.text || 'Пост сгенерирован ИИ'}</p>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span><Calendar size={12} className="inline mr-1" />{new Date(post.scheduledAt).toLocaleString()}</span>
                    <span>{post.accountIds.length} аккаунтов</span>
                  </div>
                </div>
                {post.status === 'pending' && (
                  <button onClick={() => removeScheduledPost(post.id)} className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Post Modal */}
      {show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md" onClick={() => setShow(false)}>
          <div className="bg-slate-950 border border-slate-900 rounded-3xl p-6 w-[720px] max-w-full shadow-2xl relative max-h-[92vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-slate-100">Создать публикацию 2.0</h3>
              <button onClick={() => setShow(false)} className="text-slate-500 hover:text-slate-200 transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <div className="space-y-5">
              {/* Original Post Editor */}
              <div>
                <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Исходный текст поста</label>
                <div className="relative">
                  <textarea 
                    value={originalText} 
                    onChange={e => setOriginalText(e.target.value)} 
                    placeholder="Напишите базовую идею или текст поста здесь..." 
                    className="w-full bg-slate-900 border border-slate-850 rounded-xl p-3.5 pr-24 text-sm focus:outline-none focus:border-indigo-500/80 min-h-[100px] resize-none"
                  />
                  <button 
                    onClick={handleTransformAI}
                    disabled={isAdapting || !originalText.trim()}
                    className="absolute right-3 bottom-3 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-lg"
                  >
                    {isAdapting ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                    ИИ Адаптация
                  </button>
                </div>
              </div>

              {/* Tabs selectors */}
              <div className="border-b border-slate-900 pb-2">
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => setActiveTab('threads')} 
                    className={`px-4 py-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all ${
                      activeTab === 'threads' ? 'border-white text-white' : 'border-transparent text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <Layers size={14} /> Threads Thread
                  </button>
                  <button 
                    onClick={() => setActiveTab('instagram')} 
                    className={`px-4 py-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all ${
                      activeTab === 'instagram' ? 'border-pink-500 text-pink-400' : 'border-transparent text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <Instagram size={14} /> Instagram Caption
                  </button>
                  <button 
                    onClick={() => setActiveTab('whatsapp')} 
                    className={`px-4 py-2 text-xs font-bold uppercase tracking-wider flex items-center gap-2 border-b-2 transition-all ${
                      activeTab === 'whatsapp' ? 'border-emerald-500 text-emerald-400' : 'border-transparent text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <MessageCircle size={14} /> WhatsApp Channels
                  </button>
                </div>
              </div>

              {/* Tab Content Editor */}
              <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-4 min-h-[180px]">
                {activeTab === 'threads' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-400">Цепочка треда ({threadsPosts.length})</span><button onClick={addThreadPart} className="text-xs text-indigo-400 hover:underline flex items-center gap-1"><Plus size={12} /> Добавить часть</button></div>
                    {threadsPosts.map((post, i) => (
                      <div key={i} className="flex gap-2 items-start bg-slate-950/30 p-2.5 rounded-xl border border-slate-900">
                        <span className="text-xs font-mono text-slate-500 w-5 mt-2.5">#{i+1}</span>
                        <textarea 
                          value={post} 
                          onChange={e => updateThreadPart(i, e.target.value)} 
                          placeholder={`Часть ${i+1}...`} 
                          className="flex-1 bg-transparent border-0 focus:ring-0 text-sm text-slate-200 resize-none min-h-[60px] focus:outline-none"
                        />
                        {threadsPosts.length > 1 && (
                          <button onClick={() => removeThreadPart(i)} className="text-slate-500 hover:text-rose-400 p-1 rounded"><Trash2 size={12} /></button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'instagram' && (
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Подпись (Caption)</label>
                      <textarea 
                        value={igCaption} 
                        onChange={e => setIgCaption(e.target.value)} 
                        placeholder="Подпись для Instagram..." 
                        className="w-full bg-slate-950/40 border border-slate-900 rounded-xl p-3 text-sm focus:outline-none focus:border-indigo-500/80 min-h-[80px] resize-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Хэштеги (через пробел)</label>
                      <input 
                        type="text" 
                        value={igTags.join(' ')} 
                        onChange={e => setIgTags(e.target.value.split(' ').filter(Boolean))} 
                        placeholder="#marketing #smm #startup" 
                        className="w-full bg-slate-950/40 border border-slate-900 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-indigo-500/80 font-mono"
                      />
                    </div>
                  </div>
                )}

                {activeTab === 'whatsapp' && (
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Текст сообщения (поддерживает *жирный*)</label>
                      <textarea 
                        value={waText} 
                        onChange={e => setWaText(e.target.value)} 
                        placeholder="WhatsApp структурированное сообщение..." 
                        className="w-full bg-slate-950/40 border border-slate-900 rounded-xl p-3 text-sm focus:outline-none focus:border-indigo-500/80 min-h-[80px] resize-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Call-To-Action (Ссылка / Кнопка)</label>
                      <input 
                        type="text" 
                        value={waCTA} 
                        onChange={e => setWaCTA(e.target.value)} 
                        placeholder="Например: Узнать подробности: https://my-saas.com" 
                        className="w-full bg-slate-950/40 border border-slate-900 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Media input */}
              <div>
                <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Ссылка на изображение (для Instagram и Threads)</label>
                <input 
                  type="text" 
                  value={mediaUrl} 
                  onChange={e => setMediaUrl(e.target.value)} 
                  placeholder="https://my-cdn.com/post-banner.jpg" 
                  className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                />
              </div>

              {/* Schedule and Accounts selectors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Выбор аккаунтов</label>
                  <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto">
                    {active.map(acc => (
                      <button 
                        key={acc.id} 
                        onClick={() => toggleAccount(acc.id)} 
                        className={`flex items-center gap-2 p-2 rounded-xl text-xs font-semibold transition-all border ${
                          selectedAccounts.includes(acc.id) 
                            ? 'bg-indigo-500/15 border-indigo-500/35 text-indigo-400' 
                            : 'bg-slate-950/40 border-slate-900 text-slate-400 hover:text-slate-300'
                        }`}
                      >
                        <span className="text-[10px] uppercase font-bold text-slate-500">{acc.platform[0]}</span>
                        <span className="truncate">@{acc.username}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Планирование (Оставьте пустым для мгновенного поста)</label>
                  <div className="grid grid-cols-2 gap-2">
                    <input type="date" value={scheduleDate} onChange={e => setScheduleDate(e.target.value)} className="bg-slate-900 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none" />
                    <input type="time" value={scheduleTime} onChange={e => setScheduleTime(e.target.value)} className="bg-slate-900 border border-slate-850 rounded-xl px-3 py-2 text-xs focus:outline-none" />
                  </div>
                </div>
              </div>

              {/* Send buttons */}
              <div className="flex gap-3 pt-3">
                <button onClick={() => setShow(false)} className="py-2.5 bg-slate-900 hover:bg-slate-850 text-slate-300 rounded-xl text-sm font-semibold flex-1">Отмена</button>
                <button 
                  onClick={handleCreate} 
                  disabled={selectedAccounts.length === 0}
                  className="py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white rounded-xl text-sm font-bold flex-1 flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/10"
                >
                  <Send size={15} />
                  {scheduleDate ? 'Запланировать' : 'Опубликовать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
