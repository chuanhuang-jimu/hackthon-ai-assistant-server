
import React, { useState, useEffect, useMemo, useCallback } from 'react';

// 为保证“仅仅修改 MorningBrief.tsx”且“代码可运行”，在此内联所需的类型定义和配置
interface SmartInfo {
  id: string;
  title: string;
  is_urgent: boolean;
  is_mentioned: boolean;
  time_text: string;
  source_label: string;
  icon_type: string;
  summary?: string;
  gmail_link?: string;
}

interface MorningBriefData {
  ai_summary: string;
  items: SmartInfo[];
}

interface TodoItem {
  id: string;
  title: string;
  summary?: string;
  source: 'email' | 'manual';
  sourceId?: string;
  completed: boolean;
}

const API_ENDPOINTS = {
  READ_EMAIL: 'http://127.0.0.1:8200/api/gemini/email/read'
};

const REDIS_BASE_URL = 'http://localhost:8200/api/redis';
const PROCESSED_IDS_KEY = 'emailProcessedIds';
const TODO_ITEMS_KEY = 'todoItems';
const CACHE_KEY = 'emailQuickReadCache';
const CACHE_DURATION_MS = 30 * 60 * 1000; // 30 minutes

interface CachedData {
  data: MorningBriefData;
  timestamp: number;
}

const EmailQuickRead: React.FC = () => {
  const [data, setData] = useState<MorningBriefData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [expandedItemId, setExpandedItemId] = useState<string | null>(null);
  const [processedItemIds, setProcessedItemIds] = useState<string[]>([]);
  const [isProcessedCollapsed, setIsProcessedCollapsed] = useState(true);
  const [isTodoCollapsed, setIsTodoCollapsed] = useState(false);
  const [todoItems, setTodoItems] = useState<TodoItem[]>([]);
  const [newTodoText, setNewTodoText] = useState('');
  const [editingTodoId, setEditingTodoId] = useState<string | null>(null);
  const [editingTodoText, setEditingTodoText] = useState('');

  const mockFullData: MorningBriefData = {
    "ai_summary": "周日好！自上周五以来，共有 11 项高优先级动态，其中 Jira 上有 3 项提及或分配，GitLab 有 7 项 Code Review 相关通知，Wiki 上有 1 项 @提及。此外还有一些Jira任务的状态更新和Confluence页面编辑的通知。",
    "items": [
      { "id": "10447", "title": "[Confluence] Veeva Orion > Plum Retro 2026-01-16", "is_urgent": true, "is_mentioned": true, "time_text": "周五 17:50", "source_label": "Wiki", "icon_type": "email", "summary": "这是一个关于Confluence页面更新的摘要。详细内容请点击查看。", "gmail_link": "https://mail.google.com/mail/u/0/#all/19c0778c7e89c415" },
      { "id": "10104", "title": "[JIRA] Minglei Weng mentioned you on ORI-134717 (Jira)", "is_urgent": true, "is_mentioned": true, "time_text": "周五 17:02", "source_label": "Jira", "icon_type": "email", "summary": "您在Jira任务ORI-134717中被Minglei Weng提及。请登录Jira查看详情。", "gmail_link": "https://mail.google.com/mail/u/0/#all/19c0778c7e89c416" },
      { "id": "9424", "title": "Re: chinasfa | ORI-136228: improved robustness (!34202)", "is_urgent": true, "is_mentioned": true, "time_text": "周五 14:38", "source_label": "GitLab", "icon_type": "email", "summary": "GitLab上关于PR #34202的Code Review，主要涉及健壮性改进。", "gmail_link": "https://mail.google.com/mail/u/0/#all/19c0778c7e89c415" },
      { "id": "9408", "title": "Re: chinasfa | ORI-135104 feat: allow overriding metadata reference condition via page layout config (!34148)", "is_urgent": true, "is_mentioned": true, "time_text": "周五 11:26", "source_label": "GitLab", "icon_type": "email", "summary": "GitLab上关于PR #34148的Code Review，实现通过页面布局配置覆盖元数据引用条件。", "gmail_link": "https://mail.google.com/mail/u/0/#all/19c0778c7e89c415" }
    ]
  };
  const fetchFromRedis = async (key: string) => {
    try {
      const response = await fetch(`${REDIS_BASE_URL}/get?key=${key}`);
      if (!response.ok) return null;
      const result = await response.json();
      return result.success ? result.data : null;
    } catch (error) {
      console.error(`Failed to fetch ${key} from Redis:`, error);
      return null;
    }
  };
  
  const saveToRedis = async (key: string, value: any) => {
    try {
      await fetch(`${REDIS_BASE_URL}/set`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ key, value }),
      });
    } catch (error) {
      console.error(`Failed to save ${key} to Redis:`, error);
    }
  };

  const tryExtractJson = (str: string) => {
    try {
      const start = str.indexOf('{');
      const end = str.lastIndexOf('}');
      if (start === -1 || end === -1) return null;
      const jsonCandidate = str.substring(start, end + 1);
      return JSON.parse(jsonCandidate);
    } catch (e) {
      console.error("Extraction failed for string:", str.substring(0, 100) + "...", e);
      return null;
    }
  };

  const fetchData = useCallback(async (force = false) => {
    if (!force) setLoading(true);
    else setIsRefreshing(true);

    try {
      const response = await fetch(API_ENDPOINTS.READ_EMAIL);
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) throw new Error("API returned HTML.");

      const rawText = await response.text();
      const result = tryExtractJson(rawText);

      let newData: MorningBriefData | null = null;
      if (result && result.success && result.response) {
        const parsedData = typeof result.response === 'string' ? tryExtractJson(result.response) : result.response;
        if (parsedData) newData = parsedData;
        else throw new Error("Could not parse inner response data");
      } else {
        console.warn('API returned unsuccessful response, using fallback.');
        newData = mockFullData;
      }
      
      if (newData) {
        setData(newData);
        saveToRedis(CACHE_KEY, { data: newData, timestamp: new Date().getTime() });
      }
    } catch (error) {
      console.error('Fetch error:', error);
      setData(prevData => prevData || mockFullData);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const loadInitialData = async () => {
      const [processed, todos, cachedItem] = await Promise.all([
        fetchFromRedis(PROCESSED_IDS_KEY),
        fetchFromRedis(TODO_ITEMS_KEY),
        fetchFromRedis(CACHE_KEY)
      ]);

      if (processed) setProcessedItemIds(processed);
      if (todos) setTodoItems(todos);

      if (cachedItem) {
        try {
          const cache: CachedData = cachedItem;
          const isCacheStale = (new Date().getTime() - cache.timestamp) > CACHE_DURATION_MS;
          
          setData(cache.data);
          setLoading(false);
  
          if (isCacheStale) {
            fetchData(true);
          }
        } catch (e) {
          console.error("Failed to parse cache", e);
          fetchData();
        }
      } else {
        fetchData();
      }
    };

    loadInitialData();
    
  }, [fetchData]);

  const { unprocessedItems, processedItems } = useMemo(() => {
    if (!data) return { unprocessedItems: [], processedItems: [] };
    
    const sourceOrder: Record<string, number> = { 'jira': 0, 'gitlab': 1, 'wiki': 2 };
    const sorted = [...data.items].sort((a, b) => {
        const aPriority = (a.is_urgent ? 2 : 0) + (a.is_mentioned ? 1 : 0);
        const bPriority = (b.is_urgent ? 2 : 0) + (b.is_mentioned ? 1 : 0);
        if (aPriority !== bPriority) return bPriority - aPriority;
        const aSourceRank = sourceOrder[a.source_label?.toLowerCase()] ?? 99;
        const bSourceRank = sourceOrder[b.source_label?.toLowerCase()] ?? 99;
        if (aSourceRank !== bSourceRank) return aSourceRank - bSourceRank;
        return parseInt(b.id) - parseInt(a.id);
    });

    const unprocessed = sorted.filter(item => !processedItemIds.includes(item.id));
    const processed = sorted.filter(item => processedItemIds.includes(item.id));
    
    return { unprocessedItems: unprocessed, processedItems: processed };
  }, [data, processedItemIds]);

  const updateTodoItems = (newItems: TodoItem[]) => {
    setTodoItems(newItems);
    saveToRedis(TODO_ITEMS_KEY, newItems);
  };

  const addTodoFromEmail = (item: SmartInfo) => {
    const newTodo: TodoItem = {
      id: `todo-${Date.now()}`,
      title: item.title,
      summary: item.summary,
      source: 'email',
      sourceId: item.id,
      completed: false,
    };
    updateTodoItems([...todoItems, newTodo]);
  };

  const handleManualTodoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTodoText.trim()) return;
    const newTodo: TodoItem = {
      id: `todo-${Date.now()}`,
      title: newTodoText,
      source: 'manual',
      completed: false,
    };
    updateTodoItems([...todoItems, newTodo]);
    setNewTodoText('');
  };

  const toggleTodoCompleted = (todoId: string) => {
    const newItems = todoItems.map(item =>
      item.id === todoId ? { ...item, completed: !item.completed } : item
    );
    updateTodoItems(newItems);
  };

  const removeTodoItem = (todoId: string) => {
    const newItems = todoItems.filter(item => item.id !== todoId);
    updateTodoItems(newItems);
  };

  const handleStartEdit = (todo: TodoItem) => {
    setEditingTodoId(todo.id);
    setEditingTodoText(todo.title);
  };

  const handleSaveEdit = () => {
    if (!editingTodoId) return;
    const newItems = todoItems.map(item =>
      item.id === editingTodoId ? { ...item, title: editingTodoText } : item
    );
    updateTodoItems(newItems);
    setEditingTodoId(null);
    setEditingTodoText('');
  };

  const handleEditKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      setEditingTodoId(null);
      setEditingTodoText('');
    }
  };

  const handleSetProcessed = (itemId: string, process = true) => {
    const newProcessedIds = process
      ? [...processedItemIds, itemId]
      : processedItemIds.filter(id => id !== itemId);
    
    setProcessedItemIds(newProcessedIds);
    saveToRedis(PROCESSED_IDS_KEY, newProcessedIds);
    if (process) {
      setExpandedItemId(null);
    }
  };

  const stats = useMemo(() => {
    if (!data) return { mentioned: 0, urgent: 0, jira: 0, gitlab: 0, wiki: 0, others: 0 };
    const itemsToCount = data.items.filter(item => !processedItemIds.includes(item.id));
    const res = { mentioned: 0, urgent: 0, jira: 0, gitlab: 0, wiki: 0, others: 0 };
    itemsToCount.forEach(item => {
      if (item.is_mentioned) res.mentioned++;
      if (item.is_urgent) res.urgent++;
      const src = item.source_label?.toLowerCase() || 'other';
      if (src === 'jira') res.jira++;
      else if (src === 'gitlab') res.gitlab++;
      else if (src === 'wiki') res.wiki++;
      else res.others++;
    });
    return res;
  }, [data, processedItemIds]);

  const getSourceIconClass = (label: string) => {
    switch (label?.toLowerCase()) {
      case 'gitlab': return 'fa-brands fa-gitlab';
      case 'jira': return 'fa-brands fa-jira';
      case 'wiki': return 'fa-solid fa-book-open';
      default: return 'fa-solid fa-envelope';
    }
  };

  const getSourceColor = (label: string) => {
    switch (label?.toLowerCase()) {
      case 'gitlab': return 'bg-orange-50 text-orange-600';
      case 'jira': return 'bg-blue-50 text-blue-600';
      case 'wiki': return 'bg-emerald-50 text-emerald-600';
      default: return 'bg-slate-50 text-slate-600';
    }
  };

  const priorityStats = [
    { label: '@提及', count: stats.mentioned, icon: 'fa-at', color: 'blue' },
    { label: '高优', count: stats.urgent, icon: 'fa-bolt', color: 'rose' },
  ];

  const sourceStats = [
    { label: 'Jira', count: stats.jira, icon: 'fa-jira', isBrand: true },
    { label: 'GitLab', count: stats.gitlab, icon: 'fa-gitlab', isBrand: true },
    { label: 'Wiki', count: stats.wiki, icon: 'fa-book-open' },
    { label: '其他', count: stats.others, icon: 'fa-ellipsis' },
  ];

  const toggleExpand = (itemId: string) => {
    setExpandedItemId(prevId => (prevId === itemId ? null : itemId));
  };
  
  const isEmailInTodo = (emailId: string) => todoItems.some(todo => todo.source === 'email' && todo.sourceId === emailId);

  const renderItem = (item: SmartInfo, isProcessed: boolean) => (
    <div key={item.id} className={isProcessed ? 'filter grayscale opacity-70' : ''}>
      <div 
        className="p-4 flex items-start gap-4 hover:bg-slate-50 transition-colors cursor-pointer group"
        onClick={() => toggleExpand(item.id)}
      >
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border border-transparent group-hover:border-slate-200 transition-all ${getSourceColor(item.source_label)}`}>
          <i className={`${getSourceIconClass(item.source_label)}`}></i>
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h4 className="text-sm font-semibold text-slate-800 truncate leading-tight">{item.title}</h4>
          </div>
          
          {!isProcessed && (
            <div className="flex items-center gap-2 mb-2">
              {item.is_urgent && <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-red-100 text-red-600 uppercase tracking-tighter shadow-sm border border-red-200/50">高优</span>}
              {item.is_mentioned && <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-blue-100 text-blue-600 uppercase tracking-tighter shadow-sm border border-blue-200/50">@提及</span>}
            </div>
          )}

          <div className="flex items-center gap-3">
            <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1"><i className="fa-regular fa-clock opacity-70"></i>{item.time_text}</span>
            <span className="text-slate-200 text-xs">•</span>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">{item.source_label}</span>
          </div>
        </div>

        <div className="opacity-0 group-hover:opacity-100 transition-opacity self-center">
          <div className="w-8 h-8 rounded-full bg-white border shadow-sm flex items-center justify-center text-slate-400 hover:text-blue-600">
            <i className={`fa-solid ${expandedItemId === item.id ? 'fa-chevron-up' : 'fa-chevron-right'} text-xs`}></i>
          </div>
        </div>
      </div>
      {expandedItemId === item.id && (
        <div className="p-4 pt-0 pl-16 bg-slate-50 border-t border-slate-100">
          {item.summary && <p className="text-sm text-slate-600 mb-3">{item.summary}</p>}
          <div className="flex items-center gap-2 flex-wrap">
            {item.gmail_link && (
              <a 
                href={item.gmail_link} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="inline-flex items-center px-3 py-1.5 border border-blue-200 rounded-lg text-blue-600 text-xs font-medium bg-blue-50 hover:bg-blue-100 transition-colors"
                onClick={(e) => e.stopPropagation()}
              >
                <i className="fa-solid fa-external-link-alt mr-2"></i>
                在 Gmail 中查看
              </a>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSetProcessed(item.id, !isProcessed);
              }}
              className={`inline-flex items-center px-3 py-1.5 border rounded-lg text-xs font-medium transition-colors ${
                isProcessed 
                  ? 'border-gray-300 bg-gray-100 text-gray-600 hover:bg-gray-200'
                  : 'border-green-200 bg-green-50 text-green-600 hover:bg-green-100'
              }`}
            >
              <i className={`fa-solid ${isProcessed ? 'fa-undo' : 'fa-check'} mr-2`}></i>
              {isProcessed ? '撤销处理' : '标记为已处理'}
            </button>
            {!isProcessed && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  addTodoFromEmail(item);
                }}
                disabled={isEmailInTodo(item.id)}
                className="inline-flex items-center px-3 py-1.5 border rounded-lg text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed border-purple-200 bg-purple-50 text-purple-600 hover:bg-purple-100"
              >
                <i className="fa-solid fa-calendar-plus mr-2"></i>
                {isEmailInTodo(item.id) ? '已加入' : '加入待办'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      <div className="space-y-6 animate-in fade-in slide-in-from-top-4 duration-500">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {priorityStats.map((stat, idx) => (
              <div key={idx} className="bg-white border rounded-2xl p-4 shadow-sm flex items-center gap-4 transition-all hover:shadow-md group cursor-default">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-${stat.color}-50 text-${stat.color}-600 group-hover:scale-110 transition-transform`}>
                  <i className={`fa-solid ${stat.icon} text-lg`}></i>
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-tighter block">{stat.label}</span>
                  <span className={`text-2xl font-black text-slate-800 ${(loading && !data) ? 'animate-pulse bg-slate-100 rounded w-8 h-8 inline-block' : ''}`}>
                    {!(loading && !data) && stat.count}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-slate-50 border rounded-2xl p-3 shadow-sm flex items-center justify-around md:justify-start md:gap-12 px-8 overflow-x-auto no-scrollbar">
            {sourceStats.map((stat, idx) => (
              <div key={idx} className="flex items-center gap-2 group whitespace-nowrap">
                <div className="w-6 h-6 rounded flex items-center justify-center text-slate-400 group-hover:text-slate-600 transition-colors">
                  <i className={`${stat.isBrand ? 'fa-brands' : 'fa-solid'} ${stat.icon} text-sm`}></i>
                </div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">{stat.label}</span>
                <span className={`text-sm font-black text-slate-700 min-w-[1ch] ${(loading && !data) ? 'animate-pulse bg-slate-200 rounded w-4 h-4' : ''}`}>
                  {!(loading && !data) && stat.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-blue-100 p-6 rounded-2xl shadow-sm">
          <div className="flex items-center gap-2 mb-3 text-blue-700">
            <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
              <i className="fa-solid fa-wand-sparkles text-sm"></i>
            </div>
            <h2 className="font-bold text-sm uppercase tracking-wider">晨间 AI 智能综述</h2>
          </div>
          <p className={`text-slate-700 leading-relaxed font-medium text-sm md:text-base min-h-[3rem] ${loading && !data ? 'animate-pulse bg-slate-200/50 rounded' : ''}`}>
            {loading && !data ? '' : data?.ai_summary}
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-700">动态提醒</h3>
              <span className="bg-slate-200 text-slate-600 text-[10px] px-2 py-0.5 rounded-full font-bold">
                {unprocessedItems.length || 0}
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-tighter">实时同步自外部工作流</span>
          </div>
          
          <div className="divide-y divide-slate-50 overflow-hidden">
            {loading && !data ? (
              Array(5).fill(0).map((_, i) => (
                <div key={i} className="p-4 flex gap-4 animate-pulse"><div className="w-10 h-10 rounded-full bg-slate-100 shrink-0"></div><div className="flex-1 space-y-2"><div className="h-4 bg-slate-100 rounded w-3/4"></div><div className="h-3 bg-slate-50 rounded w-1/4"></div></div></div>
              ))
            ) : unprocessedItems.length > 0 ? (
                unprocessedItems.map((item) => renderItem(item, false))
            ) : (
                <p className="p-12 text-sm text-slate-400 text-center italic">所有动态都已处理完毕！</p>
            )}
          </div>
        </div>

        {/* --- 待办事项区域 --- */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div 
            className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center cursor-pointer hover:bg-slate-100 transition-colors"
            onClick={() => setIsTodoCollapsed(!isTodoCollapsed)}
          >
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-600">待办事项</h3>
              <span className="bg-purple-100 text-purple-600 text-[10px] px-2 py-0.5 rounded-full font-bold">
                {todoItems.filter(i => !i.completed).length}
              </span>
            </div>
            <i className={`fa-solid fa-chevron-down text-xs text-slate-400 transition-transform ${isTodoCollapsed ? '' : 'rotate-180'}`}></i>
          </div>
          {!isTodoCollapsed && (
            <div className="divide-y divide-slate-100">
              <div className="p-4">
                <form onSubmit={handleManualTodoSubmit} className="flex gap-2">
                  <input
                    type="text"
                    value={newTodoText}
                    onChange={(e) => setNewTodoText(e.target.value)}
                    placeholder="添加新的待办事项..."
                    className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 transition"
                  />
                  <button type="submit" className="px-4 py-2 bg-purple-500 text-white font-semibold rounded-lg text-sm hover:bg-purple-600 transition-colors disabled:opacity-50" disabled={!newTodoText.trim()}>
                    添加
                  </button>
                </form>
              </div>
              {todoItems.length > 0 ? (
                todoItems.map(todo => (
                  <div key={todo.id} className="p-4 flex items-start gap-4 group">
                    <input 
                      type="checkbox"
                      checked={todo.completed}
                      onChange={() => toggleTodoCompleted(todo.id)}
                      className="w-5 h-5 rounded-md border-slate-300 text-purple-500 focus:ring-purple-400 mt-1"
                    />
                    <div className="flex-1 min-w-0">
                       {editingTodoId === todo.id ? (
                         <input
                           type="text"
                           value={editingTodoText}
                           onChange={(e) => setEditingTodoText(e.target.value)}
                           onBlur={handleSaveEdit}
                           onKeyDown={handleEditKeyDown}
                           className="w-full px-2 py-1 border border-purple-300 rounded-md text-sm"
                           autoFocus
                         />
                       ) : (
                         <p 
                           className={`text-sm text-slate-700 cursor-pointer ${todo.completed ? 'line-through text-slate-400' : 'font-medium'}`}
                           onDoubleClick={() => handleStartEdit(todo)}
                         >
                           {todo.title}
                         </p>
                       )}
                       {todo.summary && <p className="text-xs text-slate-500 mt-1">{todo.summary}</p>}
                       {todo.source === 'email' && (
                         <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1 inline-block">来自邮件</span>
                       )}
                    </div>
                    <button onClick={() => removeTodoItem(todo.id)} className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                      <i className="fa-solid fa-trash-can"></i>
                    </button>
                  </div>
                ))
              ) : (
                <p className="p-8 text-sm text-slate-400 text-center italic">没有待办事项。</p>
              )}
            </div>
          )}
        </div>
        
        {processedItems.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden opacity-80">
            <div 
              className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center cursor-pointer hover:bg-slate-100 transition-colors"
              onClick={() => setIsProcessedCollapsed(!isProcessedCollapsed)}
            >
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-600">已处理动态</h3>
                <span className="bg-slate-200 text-slate-500 text-[10px] px-2 py-0.5 rounded-full font-bold">
                  {processedItems.length}
                </span>
              </div>
              <i className={`fa-solid fa-chevron-down text-xs text-slate-400 transition-transform ${isProcessedCollapsed ? '' : 'rotate-180'}`}></i>
            </div>
            {!isProcessedCollapsed && (
              <div className="divide-y divide-slate-50 overflow-hidden">
                {processedItems.map((item) => renderItem(item, true))}
              </div>
            )}
          </div>
        )}

        <div className="text-center pb-4">
          <p className="text-[10px] text-slate-300 font-bold uppercase tracking-widest italic">没有更多动态了</p>
        </div>
      </div>
      
      <button
        onClick={() => fetchData(true)}
        disabled={isRefreshing}
        className="fixed bottom-8 right-8 w-14 h-14 bg-indigo-600 text-white rounded-full shadow-xl flex items-center justify-center hover:bg-indigo-700 transition-all transform hover:scale-110 active:scale-95 disabled:bg-slate-300 disabled:cursor-not-allowed z-50 group"
        aria-label="Refresh Data"
      >
        <i className={`fa-solid fa-sync text-lg ${isRefreshing ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`}></i>
      </button>
    </>
  );
};

export default EmailQuickRead;
