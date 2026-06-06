'use client';

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { Target, Plus, Trash2, ToggleLeft, ToggleRight, Sparkles, CheckCircle2, XCircle, Search, FileText } from 'lucide-react';

interface Rule {
  id: number;
  user_id: number;
  social_account_id: number | null;
  trigger_keyword: string;
  match_type: 'exact' | 'contains';
  response_type: 'dm' | 'comment';
  response_text: string;
  guide_file_url: string | null;
  is_active: number;
  created_at: string;
}

interface Lead {
  id: number;
  user_id: number;
  auto_reply_id: number;
  conversation_id: number | null;
  recipient_external_id: string;
  status: 'sent' | 'failed';
  created_at: string;
  trigger_keyword: string;
  response_text: string;
  external_username: string | null;
  platform: 'threads' | 'instagram' | 'whatsapp' | null;
}

export default function LeadGenSettings() {
  const { accounts, fetchAccounts } = useStore();
  const [rules, setRules] = useState<Rule[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  
  const [showAddForm, setShowAddForm] = useState(false);
  const [keyword, setKeyword] = useState('');
  const [responseMsg, setResponseMsg] = useState('');
  const [matchType, setMatchType] = useState<'exact' | 'contains'>('exact');
  const [responseType, setResponseType] = useState<'dm' | 'comment'>('dm');
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [guideUrl, setGuideUrl] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [activeTab, setActiveTab] = useState<'rules' | 'leads'>('rules');
  const [searchQuery, setSearchQuery] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const resRules = await fetch('/api/leadgen/rules');
      if (resRules.ok) {
        const data = await resRules.json();
        setRules(data.rules || []);
      }
      
      const resLeads = await fetch('/api/leadgen/leads');
      if (resLeads.ok) {
        const data = await resLeads.json();
        setLeads(data.leads || []);
      }
    } catch (err) {
      console.error('Failed to load leadgen data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
    loadData();
  }, []);

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim() || !responseMsg.trim()) {
      setErrorMsg('Пожалуйста, заполните ключевое слово и текст ответа.');
      return;
    }
    
    setErrorMsg('');
    setSuccessMsg('');
    setLoading(true);
    
    try {
      const res = await fetch('/api/leadgen/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          social_account_id: selectedAccount ? parseInt(selectedAccount) : null,
          trigger_keyword: keyword,
          match_type: matchType,
          response_type: responseType,
          response_text: responseMsg,
          guide_file_url: guideUrl
        })
      });
      
      if (res.ok) {
        setSuccessMsg('Правило автоответа успешно добавлено!');
        setKeyword('');
        setResponseMsg('');
        setGuideUrl('');
        setSelectedAccount('');
        setShowAddForm(false);
        await loadData();
      } else {
        const data = await res.json();
        setErrorMsg(data.detail || 'Ошибка при добавлении правила.');
      }
    } catch (err) {
      setErrorMsg('Системная ошибка сети.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = async (id: number) => {
    if (!confirm('Вы уверены, что хотите удалить это правило?')) return;
    try {
      const res = await fetch(`/api/leadgen/rules/${id}`, { method: 'DELETE' });
      if (res.ok) {
        await loadData();
      }
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleToggleRule = async (rule: Rule) => {
    const nextStatus = rule.is_active === 1 ? 0 : 1;
    try {
      const res = await fetch(`/api/leadgen/rules/${rule.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: nextStatus })
      });
      if (res.ok) {
        setRules(rules.map(r => r.id === rule.id ? { ...r, is_active: nextStatus } : r));
      }
    } catch (err) {
      console.error('Toggle failed:', err);
    }
  };

  const filteredLeads = leads.filter(lead => {
    const term = searchQuery.toLowerCase();
    return (
      (lead.external_username || '').toLowerCase().includes(term) ||
      (lead.recipient_external_id || '').toLowerCase().includes(term) ||
      lead.trigger_keyword.toLowerCase().includes(term) ||
      lead.response_text.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Target className="text-purple-400" /> LeadGen Autopilot
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Автоматические рассылки лид-магнитов и гайдов в ответ на триггер-слова клиентов.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('rules')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 ${
              activeTab === 'rules'
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/30'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-white'
            }`}
          >
            Правила автоответа
          </button>
          <button
            onClick={() => setActiveTab('leads')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 ${
              activeTab === 'leads'
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/30'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:text-white'
            }`}
          >
            Собрано лидов
            {leads.length > 0 && (
              <span className="ml-2 bg-purple-900 text-purple-300 text-xs px-2 py-0.5 rounded-full font-bold">
                {leads.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl border border-red-500/20 bg-red-950/20 text-red-400 text-sm">
          ⚠️ {errorMsg}
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-950/20 text-emerald-400 text-sm">
          ✓ {successMsg}
        </div>
      )}

      {activeTab === 'rules' ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-white">Список триггеров</h3>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-white px-4 py-2 rounded-xl text-sm font-medium transition-all"
            >
              <Plus size={16} /> Добавить триггер
            </button>
          </div>

          {showAddForm && (
            <form onSubmit={handleAddRule} className="p-6 rounded-2xl border border-slate-800/80 bg-slate-950/60 backdrop-blur-md space-y-4 max-w-2xl animate-in fade-in slide-in-from-top-4 duration-200">
              <h4 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Sparkles size={14} className="text-purple-400 animate-pulse" /> Новый автоответчик
              </h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ключевое слово (триггер)</label>
                  <input
                    type="text"
                    placeholder="Пример: ХОЧУ"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/80 transition-all text-sm font-medium"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Тип совпадения</label>
                  <select
                    value={matchType}
                    onChange={(e) => setMatchType(e.target.value as any)}
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-purple-500/80 transition-all text-sm font-medium"
                  >
                    <option value="exact">Точное совпадение (Exact)</option>
                    <option value="contains">Содержит слово (Contains)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Аккаунт-источник</label>
                  <select
                    value={selectedAccount}
                    onChange={(e) => setSelectedAccount(e.target.value)}
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-purple-500/80 transition-all text-sm font-medium"
                  >
                    <option value="">Все активные аккаунты</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>
                        {acc.username} ({acc.platform.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Где отвечать</label>
                  <select
                    value={responseType}
                    onChange={(e) => setResponseType(e.target.value as any)}
                    className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-purple-500/80 transition-all text-sm font-medium"
                  >
                    <option value="dm">В личные сообщения (Direct / DM)</option>
                    <option value="comment">Ответить на комментарий (Reply)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ответное сообщение</label>
                <textarea
                  placeholder="Привет! Спасибо за интерес. Держи обещанную ссылку на руководство..."
                  value={responseMsg}
                  onChange={(e) => setResponseMsg(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/80 transition-all text-sm font-medium resize-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Ссылка на лид-магнит / файл (Необязательно)</label>
                <input
                  type="text"
                  placeholder="https://yourdomain.com/freebie-guide.pdf"
                  value={guideUrl}
                  onChange={(e) => setGuideUrl(e.target.value)}
                  className="w-full bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/80 transition-all text-sm font-medium"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white border border-slate-800 text-sm font-medium transition-all"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-xl bg-purple-600 text-white hover:bg-purple-500 text-sm font-medium transition-all shadow-md shadow-purple-900/20"
                >
                  {loading ? 'Создание...' : 'Сохранить триггер'}
                </button>
              </div>
            </form>
          )}

          {rules.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-950/40">
              <Target size={48} className="mx-auto text-slate-600 mb-4 animate-bounce" />
              <h4 className="text-white font-medium text-lg">Нет настроенных триггеров</h4>
              <p className="text-slate-400 text-sm mt-1 max-w-md mx-auto">
                Создайте первое правило автоответчика. Пользователи смогут писать ключевые слова в комментариях и получать подарки!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {rules.map(rule => {
                const acc = accounts.find(a => String(a.id) === String(rule.social_account_id));
                return (
                  <div key={rule.id} className="p-5 rounded-2xl border border-slate-800 bg-slate-950/30 flex flex-col justify-between hover:border-slate-700/60 transition-all group">
                    <div className="space-y-3">
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-2">
                          <span className="bg-purple-950 text-purple-300 text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider">
                            {rule.trigger_keyword}
                          </span>
                          <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
                            {rule.match_type === 'exact' ? 'Точное' : 'Содержит'}
                          </span>
                        </div>
                        <button
                          onClick={() => handleToggleRule(rule)}
                          className="text-slate-500 hover:text-purple-400 transition-colors"
                        >
                          {rule.is_active === 1 ? (
                            <ToggleRight size={24} className="text-purple-500" />
                          ) : (
                            <ToggleLeft size={24} className="text-slate-600" />
                          )}
                        </button>
                      </div>

                      <p className="text-slate-300 text-sm line-clamp-3 font-medium">
                        "{rule.response_text}"
                      </p>
                      
                      {rule.guide_file_url && (
                        <div className="flex items-center gap-1.5 text-xs text-purple-400 font-semibold bg-purple-950/25 px-2 py-1 rounded-lg w-max border border-purple-500/10">
                          <FileText size={12} /> Лид-магнит прикреплен
                        </div>
                      )}
                    </div>

                    <div className="pt-4 mt-4 border-t border-slate-900/60 flex items-center justify-between text-xs text-slate-400">
                      <div>
                        <span>Канал: </span>
                        <span className="text-slate-300 font-bold">
                          {acc ? `${acc.username} (${acc.platform.toUpperCase()})` : 'Все аккаунты'}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-slate-500 hover:text-red-400 p-1.5 hover:bg-red-950/20 rounded-lg transition-all"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Leads tab */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h3 className="text-lg font-semibold text-white">Список захваченных лидов</h3>
            <div className="relative max-w-sm w-full">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
              <input
                type="text"
                placeholder="Поиск по никнейму, триггеру..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 transition-all text-sm"
              />
            </div>
          </div>

          {filteredLeads.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-950/40">
              <Target size={48} className="mx-auto text-slate-600 mb-4" />
              <h4 className="text-white font-medium text-lg">Лиды отсутствуют</h4>
              <p className="text-slate-400 text-sm mt-1">
                Никто еще не активировал автоответчики или ваш поиск не дал результатов.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-950/30">
              <table className="w-full border-collapse text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Клиент</th>
                    <th className="px-6 py-4">Платформа</th>
                    <th className="px-6 py-4">Триггер</th>
                    <th className="px-6 py-4">Отправлено</th>
                    <th className="px-6 py-4">Статус</th>
                    <th className="px-6 py-4">Дата</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900/60">
                  {filteredLeads.map(lead => (
                    <tr key={lead.id} className="hover:bg-slate-900/25 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-bold text-white">
                          @{lead.external_username || lead.recipient_external_id}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="capitalize text-xs font-semibold px-2 py-0.5 rounded-lg border bg-slate-900 border-slate-800">
                          {lead.platform || 'whatsapp'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-purple-950/60 border border-purple-800/30 text-purple-300 text-xs px-2 py-0.5 rounded-md font-bold uppercase">
                          {lead.trigger_keyword}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="max-w-xs truncate text-xs text-slate-400" title={lead.response_text}>
                          {lead.response_text}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {lead.status === 'sent' ? (
                          <span className="flex items-center gap-1 text-emerald-400 text-xs font-semibold">
                            <CheckCircle2 size={14} /> Отправлено
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-rose-400 text-xs font-semibold">
                            <XCircle size={14} /> Ошибка
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">
                        {new Date(lead.created_at).toLocaleString('ru-RU')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
