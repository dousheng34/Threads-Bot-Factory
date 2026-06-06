'use client';
import React, { useState, useEffect } from 'react';
import { useStore } from '@/lib/store';
import { Trash2, Search, Upload, Eye, EyeOff, Copy, X, Plus, Settings, MessageCircle } from 'lucide-react';
import type { ThreadsAccount } from '@/lib/types';

export default function AccountManager() {
  const { accounts, addAccount, updateAccount, removeAccount, fetchAccounts, proxies } = useStore();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [showAdd, setShowAdd] = useState(false);
  const [showTokens, setShowTokens] = useState<Record<string, boolean>>({});
  const [showWAConfig, setShowWAConfig] = useState(false);
  
  // WhatsApp form state
  const [waPhoneId, setWaPhoneId] = useState('');
  const [waToken, setWaToken] = useState('');
  const [waPhone, setWaPhone] = useState('');
  const [waUsername, setWaUsername] = useState('');

  // Manual advanced adding state
  const [isAdvanced, setIsAdvanced] = useState(false);
  const [username, setUsername] = useState('');
  const [userId, setUserId] = useState('');
  const [token, setToken] = useState('');
  const [platform, setPlatform] = useState<'threads' | 'instagram' | 'whatsapp'>('threads');

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const filtered = accounts.filter(a => 
    a.username.toLowerCase().includes(search.toLowerCase()) && 
    (filter === 'all' || a.platform === filter)
  );

  const handleMetaLogin = (plat: 'threads' | 'instagram') => {
    window.location.href = `/auth/meta?platform=${plat}`;
  };

  const handleAddWhatsApp = async () => {
    if (!waPhoneId || !waToken || !waPhone || !waUsername) {
      alert("Пожалуйста, заполните все обязательные поля!");
      return;
    }
    const settingsStr = JSON.stringify({
      phone_id: waPhoneId,
      phone_number: waPhone,
      daily_limit: 100,
    });
    
    // Add WhatsApp social account
    const acc: ThreadsAccount = {
      id: 'acc_' + Date.now(),
      platform: 'whatsapp',
      username: waUsername,
      threadsUserId: waPhoneId, // WhatsApp Phone ID acts as platform identifier
      accessToken: waToken,
      tokenExpiresAt: new Date(Date.now() + 365*24*60*60*1000).toISOString(), // 1 year
      proxyId: null,
      status: 'active',
      avatar: '',
      followers: 0,
      following: 0,
      postsCount: 0,
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      notes: settingsStr,
      dailyPostLimit: 100,
      postsToday: 0
    };
    
    await addAccount(acc);
    setShowWAConfig(false);
    setWaPhoneId('');
    setWaToken('');
    setWaPhone('');
    setWaUsername('');
  };

  const handleManualAdd = async () => {
    if (!username || !token) {
      alert("Username и Access Token обязательны!");
      return;
    }
    const acc: ThreadsAccount = {
      id: 'acc_' + Date.now(),
      platform,
      username,
      threadsUserId: userId || 'id_' + Date.now(),
      accessToken: token,
      tokenExpiresAt: new Date(Date.now() + 60*24*60*60*1000).toISOString(),
      proxyId: null,
      status: 'active',
      avatar: '',
      followers: 0,
      following: 0,
      postsCount: 0,
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      notes: '',
      dailyPostLimit: 25,
      postsToday: 0
    };
    await addAccount(acc);
    setShowAdd(false);
    setUsername('');
    setUserId('');
    setToken('');
  };

  const counts = {
    all: accounts.length,
    threads: accounts.filter(a => a.platform === 'threads').length,
    instagram: accounts.filter(a => a.platform === 'instagram').length,
    whatsapp: accounts.filter(a => a.platform === 'whatsapp').length,
  };

  return (
    <div className="space-y-6 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Подключения</h2>
          <p className="text-slate-400 text-sm mt-1">Подключите Threads, Instagram и WhatsApp для автопостинга и воронок</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setShowWAConfig(true)} 
            className="px-4 py-2 bg-emerald-600/95 hover:bg-emerald-500 text-white rounded-xl text-sm font-semibold transition-all duration-200 shadow-md shadow-emerald-900/20 flex items-center gap-2"
          >
            <MessageCircle size={16} /> Connect WhatsApp
          </button>
          <button 
            onClick={() => setShowAdd(true)} 
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all duration-200 shadow-md shadow-indigo-900/20 flex items-center gap-2"
          >
            <Plus size={16} /> Connect Meta
          </button>
        </div>
      </div>

      {/* Filter and Search */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Поиск подключенных аккаунтов..." 
            value={search} 
            onChange={e => setSearch(e.target.value)} 
            className="w-full bg-slate-900/40 border border-slate-800 rounded-xl py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-indigo-500/80 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          {Object.entries(counts).map(([s, c]) => (
            <button 
              key={s} 
              onClick={() => setFilter(s)} 
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 border ${
                filter === s 
                  ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30 shadow-sm' 
                  : 'bg-slate-950/40 text-slate-400 border-slate-800/40 hover:text-slate-300'
              }`}
            >
              {s === 'all' ? 'Все' : s} ({c})
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-950/40 border border-slate-900 rounded-2xl overflow-hidden backdrop-blur-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-900 text-xs font-semibold text-slate-400 uppercase tracking-wider bg-slate-950/20">
                <th className="p-4">Платформа</th>
                <th className="p-4">Аккаунт</th>
                <th className="p-4">Статус</th>
                <th className="p-4">Токен</th>
                <th className="p-4">Подписчики</th>
                <th className="p-4">Публикации</th>
                <th className="p-4">Действия</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(acc => (
                <tr key={acc.id} className="border-b border-slate-900/50 hover:bg-slate-900/20 transition-colors">
                  <td className="p-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-widest ${
                      acc.platform === 'threads' 
                        ? 'bg-slate-800 text-white border border-slate-700' 
                        : acc.platform === 'instagram'
                        ? 'bg-pink-500/10 text-pink-400 border border-pink-500/20'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    }`}>
                      {acc.platform}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center font-bold text-sm text-indigo-400 border border-slate-800">
                        {acc.username[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-semibold">@{acc.username}</p>
                        <p className="text-xs text-slate-500 font-mono">UID: {acc.threadsUserId}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <select 
                      value={acc.status} 
                      onChange={e => updateAccount(acc.id, { status: e.target.value as any })} 
                      className="text-xs bg-slate-950 border border-slate-850 rounded-lg px-2.5 py-1 focus:outline-none cursor-pointer text-slate-300"
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="limited">Limited</option>
                      <option value="banned">Banned</option>
                    </select>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 font-mono max-w-[120px] truncate">
                        {showTokens[acc.id] ? acc.accessToken : '••••••••••••••••'}
                      </span>
                      <button 
                        onClick={() => setShowTokens(prev => ({...prev, [acc.id]: !prev[acc.id]}))} 
                        className="text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        {showTokens[acc.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                      </button>
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(acc.accessToken);
                          alert("Токен скопирован!");
                        }} 
                        className="text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        <Copy size={13} />
                      </button>
                    </div>
                  </td>
                  <td className="p-4 text-sm font-mono">{acc.followers.toLocaleString()}</td>
                  <td className="p-4 text-sm font-mono">{acc.postsCount}</td>
                  <td className="p-4">
                    <button 
                      onClick={() => {
                        if (confirm(`Вы уверены, что хотите удалить @${acc.username}?`)) {
                          removeAccount(acc.id);
                        }
                      }} 
                      className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-all duration-200"
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="p-16 text-center text-slate-500 flex flex-col items-center justify-center">
            <Settings size={48} className="text-slate-700 animate-spin-slow mb-4 opacity-40" />
            <p className="text-sm font-medium">Подключенные аккаунты отсутствуют</p>
            <p className="text-xs text-slate-600 mt-1">Нажмите кнопку сверху, чтобы привязать соцсети.</p>
          </div>
        )}
      </div>

      {/* Meta Connection Modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowAdd(false)}>
          <div className="bg-slate-950 border border-slate-900 rounded-3xl p-6 w-[440px] max-w-full shadow-2xl relative" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-slate-100">Подключение через Meta OAuth</h3>
              <button onClick={() => setShowAdd(false)} className="text-slate-500 hover:text-slate-200 transition-colors">
                <X size={20} />
              </button>
            </div>
            
            {!isAdvanced ? (
              <div className="space-y-4">
                <p className="text-xs text-slate-400 mb-2 leading-relaxed">
                  Официальное подключение через Meta Graph API. Вы будете перенаправлены на защищенный экран авторизации Meta.
                </p>
                <button 
                  onClick={() => handleMetaLogin('threads')}
                  className="w-full py-3 bg-white text-black hover:bg-slate-100 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 shadow-md"
                >
                  Войти через Meta (Threads)
                </button>
                <button 
                  onClick={() => handleMetaLogin('instagram')}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 hover:opacity-90 text-white rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 shadow-md shadow-pink-900/10"
                >
                  Войти через Meta (Instagram)
                </button>
                <div className="pt-2 text-center">
                  <button 
                    onClick={() => setIsAdvanced(true)} 
                    className="text-xs text-indigo-400 hover:underline"
                  >
                    Ручной ввод (для разработчиков)
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Платформа</label>
                  <select 
                    value={platform} 
                    onChange={e => setPlatform(e.target.value as any)} 
                    className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                  >
                    <option value="threads">Threads</option>
                    <option value="instagram">Instagram</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Username *</label>
                  <input 
                    type="text" 
                    placeholder="username (без @)" 
                    value={username} 
                    onChange={e => setUsername(e.target.value)} 
                    className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Platform User ID</label>
                  <input 
                    type="text" 
                    placeholder="Числовой ID пользователя Meta" 
                    value={userId} 
                    onChange={e => setUserId(e.target.value)} 
                    className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Access Token *</label>
                  <input 
                    type="text" 
                    placeholder="Access Token (Маркер доступа)" 
                    value={token} 
                    onChange={e => setToken(e.target.value)} 
                    className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button onClick={() => setIsAdvanced(false)} className="py-2.5 bg-slate-900 hover:bg-slate-850 text-slate-300 rounded-xl text-sm font-semibold flex-1">Назад</button>
                  <button onClick={handleManualAdd} className="py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold flex-1">Добавить</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* WhatsApp Configuration Drawer/Modal */}
      {showWAConfig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowWAConfig(false)}>
          <div className="bg-slate-950 border border-slate-900 rounded-3xl p-6 w-[460px] max-w-full shadow-2xl relative" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-100">Подключение WhatsApp Cloud API</h3>
              <button onClick={() => setShowWAConfig(false)} className="text-slate-500 hover:text-slate-200 transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <p className="text-xs text-slate-400 mb-5 leading-relaxed">
              Укажите параметры вашего WhatsApp Business аккаунта из консоли Meta Developer. Наш вебхук для отслеживания входящих сообщений:
              <code className="block mt-1.5 p-2 bg-slate-900 rounded-lg text-indigo-400 font-mono text-[10px] break-all select-all">
                {typeof window !== 'undefined' ? `${window.location.origin}/api/webhook/whatsapp` : '/api/webhook/whatsapp'}
              </code>
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Имя канала/аккаунта *</label>
                <input 
                  type="text" 
                  placeholder="Например: Мой бизнес" 
                  value={waUsername} 
                  onChange={e => setWaUsername(e.target.value)} 
                  className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Phone Number ID *</label>
                <input 
                  type="text" 
                  placeholder="15-значный Phone ID" 
                  value={waPhoneId} 
                  onChange={e => setWaPhoneId(e.target.value)} 
                  className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Номер телефона (WhatsApp) *</label>
                <input 
                  type="text" 
                  placeholder="+79991234567" 
                  value={waPhone} 
                  onChange={e => setWaPhone(e.target.value)} 
                  className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 mb-1.5 block">Permanent Access Token *</label>
                <input 
                  type="text" 
                  placeholder="Системный токен доступа Meta" 
                  value={waToken} 
                  onChange={e => setWaToken(e.target.value)} 
                  className="w-full bg-slate-900 border border-slate-850 rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:border-indigo-500/80"
                />
              </div>
              <div className="flex gap-3 pt-3">
                <button onClick={() => setShowWAConfig(false)} className="py-2.5 bg-slate-900 hover:bg-slate-850 text-slate-300 rounded-xl text-sm font-semibold flex-1">Отмена</button>
                <button onClick={handleAddWhatsApp} className="py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-semibold flex-1">Сохранить</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
