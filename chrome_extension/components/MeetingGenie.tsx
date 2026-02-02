
import React, { useState, useEffect, useCallback } from 'react';
import { marked } from 'marked';
import { GenieSubTab, TagRule, JiraStory, AnalysisCache, BoardCache } from '../types.ts';

const DEFAULT_RULES: TagRule[] = [
  {
    id: 'rule-delay',
    tagName: 'delay',
    icon: 'fa-clock',
    color: 'rose',
    description: '延期判定标准',
    rules: [
      "从 Summary 中解析 '提测日期' 或 '计划完成' 等时间词汇",
      "若【当前时间 > 提取的时间点】且【任务状态不是 Done】则标记",
      "优先匹配 'XX.XX 提测' 这种格式的简写"
    ]
  },
  {
    id: 'rule-risk',
    tagName: 'risk',
    icon: 'fa-triangle-exclamation',
    color: 'amber',
    description: '风险识别标准',
    rules: [
      "识别评论区中包含 '阻塞'、'暂停'、'无法复现' 等关键词",
      "识别多端反馈中提到的兼容性风险（如 WeChat/Web 不一致）",
      "识别 48 小时内无任何 Worklog 且非 Done 状态的任务"
    ]
  }
];

const REDIS_BASE_URL = 'http://localhost:7379';
const REDIS_KEY_RULES = 'scrum_master_tag_rules';

const MeetingGenie: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<GenieSubTab>('board');
  const [stories, setStories] = useState<JiraStory[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<number | null>(null);
  const [analyzingKey, setAnalyzingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rules, setRules] = useState<TagRule[]>([]);
  const [selectedTagId, setSelectedTagId] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isBatchRefreshing, setIsBatchRefreshing] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<{key: string, content: string, timestamp: number} | null>(null);

  const BOARD_CACHE_KEY = 'get_jira_board_story_v3_with_expiry';
  const ANALYSIS_PREFIX = 'jira_analysis_';
  const JIRA_BASE_URL = 'https://jira.veevadev.com/browse';

  const getEndOfToday = () => {
    const now = new Date();
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
    return end.getTime();
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    const year = d.getFullYear();
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const day = d.getDate().toString().padStart(2, '0');
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    const seconds = d.getSeconds().toString().padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  const loadRules = useCallback(async () => {
    setIsInitialLoading(true);
    try {
      const response = await fetch(`${REDIS_BASE_URL}/get/${REDIS_KEY_RULES}`, {
        method: 'GET',
        mode: 'cors',
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const wrapper = await response.json();
      const redisValue = wrapper.get;
      if (redisValue) {
        const parsedRules = typeof redisValue === 'string' ? JSON.parse(redisValue) : redisValue;
        if (Array.isArray(parsedRules) && parsedRules.length > 0) {
          setRules(parsedRules);
          setSelectedTagId(parsedRules[0].id);
          return;
        }
      }
      throw new Error('No data');
    } catch (err) {
      const local = localStorage.getItem(REDIS_KEY_RULES);
      if (local) {
        const parsed = JSON.parse(local);
        setRules(parsed);
        setSelectedTagId(parsed[0]?.id || '');
      } else {
        setRules(DEFAULT_RULES);
        setSelectedTagId(DEFAULT_RULES[0].id);
      }
    } finally {
      setIsInitialLoading(false);
    }
  }, []);

  const saveRulesToRedis = async () => {
    setIsSaving(true);
    try {
      const rulesString = JSON.stringify(rules);
      localStorage.setItem(REDIS_KEY_RULES, rulesString);
      const saveUrl = `${REDIS_BASE_URL}/set/${REDIS_KEY_RULES}/${encodeURIComponent(rulesString)}`;
      const response = await fetch(saveUrl, { method: 'GET', mode: 'cors' });
      if (!response.ok) throw new Error('Save failed');
      alert('配置已成功持久化至 Redis');
    } catch (err) {
      alert('同步失败，已保存至本地。');
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => {
    loadRules();
    const cachedData = localStorage.getItem(BOARD_CACHE_KEY);
    if (cachedData) {
      try {
        const parsed: BoardCache = JSON.parse(cachedData);
        if (Date.now() < parsed.expiry) {
          setStories(parsed.data);
          setLastSyncTime(parsed.timestamp);
        } else {
          localStorage.removeItem(BOARD_CACHE_KEY);
        }
      } catch (e) {
        localStorage.removeItem(BOARD_CACHE_KEY);
      }
    }
  }, [loadRules]);

  const getValidCache = (key: string): AnalysisCache | null => {
    const cached = localStorage.getItem(`${ANALYSIS_PREFIX}${key}`);
    if (!cached) return null;
    try {
      const data: AnalysisCache = JSON.parse(cached);
      return Date.now() > data.expiry ? null : data; // Return the whole data object
    } catch (e) {
      return null;
    }
  };

  const fetchJiraStories = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://127.0.0.1:8200/api/gemini/board/story/list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt_key: "get_jira_board_story",
          mcp_servers: ["jira"],
          tag_rules: rules 
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.success && data.response) {
        let content = data.response.trim();
        const jsonBlockRegex = /```json\s+([\s\S]*?)\s+```/i;
        const match = content.match(jsonBlockRegex);
        const jsonStr = match ? match[1] : content;
        const parsed = JSON.parse(jsonStr);
        const finalData = Array.isArray(parsed) ? parsed : [];
        const now = Date.now();
        
        setStories(finalData);
        setLastSyncTime(now);
        
        localStorage.setItem(BOARD_CACHE_KEY, JSON.stringify({ 
          data: finalData, 
          timestamp: now,
          expiry: getEndOfToday() 
        }));
      }
    } catch (err: any) {
      setError(err.message || "同步失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSmartAnalysis = async (jiraId: string) => {
    setAnalyzingKey(jiraId);
    try {
      const response = await fetch('http://127.0.0.1:8200/api/gemini/story/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jira_id: jiraId }),
      });
      const data = await response.json();
      // 分析结果也可以考虑 end-of-day 过期
            localStorage.setItem(`${ANALYSIS_PREFIX}${jiraId}`, JSON.stringify({
              content: data.response || "分析完成。",
              expiry: getEndOfToday(),
              timestamp: Date.now() // Add this line
            }));    } catch (err: any) {
      console.error(err);
    } finally {
      setAnalyzingKey(null);
    }
  };

  const handleBatchRefresh = async () => {
    setIsBatchRefreshing(true);
    setError(null);
    try {
      for (const story of stories) {
        const cache = getValidCache(story.key);
        if (!cache || (Date.now() - cache.timestamp) > 6 * 60 * 60 * 1000) {
          await handleSmartAnalysis(story.key);
        }
      }
    } catch (error) {
      console.error("Batch refresh failed:", error);
      setError("批量刷新过程中断，请稍后重试。");
    } finally {
      setIsBatchRefreshing(false);
    }
  };

  const getStatusStyle = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('complete') || s.includes('done') || s.includes('resolved') || s.includes('closed')) 
      return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (s.includes('progress') || s.includes('dev')) 
      return 'text-blue-700 bg-blue-50 border-blue-200';
    if (s.includes('qa'))
      return 'text-purple-700 bg-purple-50 border-purple-200';
    return 'text-slate-600 bg-slate-50 border-slate-200';
  };

  const renderTagBadges = (storyTags?: Record<string, string[]>) => {
    if (!storyTags) return null;

    return (
      <div className="flex flex-wrap gap-1">
        {Object.entries(storyTags).map(([tagName, hitTexts]) => {
          if (!hitTexts || hitTexts.length === 0) return null;

          const ruleDef = rules.find(r => r.tagName.toLowerCase() === tagName.toLowerCase());
          if (!ruleDef) return null;

          return (
            <div key={tagName} className="relative group flex items-center w-fit">
              <div 
                className={`flex items-center gap-1 text-[9px] px-1.5 py-0.5 bg-${ruleDef.color}-50 text-${ruleDef.color}-600 border border-${ruleDef.color}-100 rounded-md font-black uppercase tracking-tighter shadow-sm cursor-help transition-all hover:bg-${ruleDef.color}-100 ${tagName === 'delay' ? 'animate-pulse' : ''}`}
              >
                <i className={`fa-solid ${ruleDef.icon} text-[8px]`}></i>
                {ruleDef.tagName}
              </div>

              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-all pointer-events-none z-50">
                <div className="bg-slate-900 text-white text-[10px] p-2 rounded-lg shadow-xl w-max max-w-[200px] leading-snug border border-white/10">
                  <div className="space-y-1">
                    {hitTexts.map((text, idx) => (
                      <div key={idx} className="flex items-start gap-1.5">
                        <div className={`mt-1.5 w-1 h-1 rounded-full bg-${ruleDef.color}-400 shrink-0`}></div>
                        <span className="opacity-95">{text}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mx-auto w-0 h-0 border-x-[4px] border-x-transparent border-t-[4px] border-t-slate-900"></div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const getRenderedMarkdown = (content: string) => {
    try {
      return { __html: marked.parse(content) as string };
    } catch (e) {
      return { __html: '<p>解析失败</p>' };
    }
  };

  const selectedRule = rules.find(r => r.id === selectedTagId);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      <div className="flex items-center gap-1 bg-slate-200/50 p-1.5 rounded-2xl w-fit">
        <button onClick={() => setActiveSubTab('board')} className={`px-6 py-2 rounded-xl text-xs font-bold transition-all ${activeSubTab === 'board' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>任务看板</button>
        <button onClick={() => setActiveSubTab('tags')} className={`px-6 py-2 rounded-xl text-xs font-bold transition-all ${activeSubTab === 'tags' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>标签管理</button>
      </div>

      {activeSubTab === 'board' ? (
        <>
          <div className="flex justify-between items-center bg-white py-5 px-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-100 shrink-0"><i className="fa-solid fa-layer-group"></i></div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-800 truncate">Scrum 看板同步</h3>
                  {lastSyncTime && (
                    <span className="text-[9px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-black uppercase tracking-tighter">
                      <i className="fa-solid fa-clock-rotate-left mr-1 opacity-60"></i>
                      获取时间: {formatTime(lastSyncTime)}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 font-medium">当前活跃: {stories.length} 个任务 (今日内有效)</p>
              </div>
            </div>
            <div className="flex items-end gap-3">
              <button onClick={fetchJiraStories} disabled={loading || isBatchRefreshing} className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition-all shadow-md shadow-indigo-100 disabled:opacity-50">{loading ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-arrows-rotate"></i>}同步看板</button>
              <div className="flex flex-col items-center">
                <span className="text-[9px] text-slate-400 mb-1">点击需谨慎，费时费token</span>
                <button onClick={handleBatchRefresh} disabled={loading || isBatchRefreshing} className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-xl text-xs font-bold hover:bg-blue-700 transition-all shadow-md shadow-blue-100 disabled:opacity-50">{isBatchRefreshing ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-wand-magic-sparkles"></i>}一键分析</button>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {stories.map((story) => {
              const hasCache = !!getValidCache(story.key);
              return (
                <div key={story.key} className="bg-white px-5 py-4 rounded-2xl border border-slate-100 shadow-sm flex items-start sm:items-center gap-4 sm:gap-6 group hover:border-indigo-200 hover:shadow-md transition-all">
                  <div className="flex flex-col gap-1.5 shrink-0 w-[110px] sm:w-[130px]">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="text-xs font-black text-indigo-600 font-mono tracking-tighter uppercase truncate shrink-0">{story.key}</span>
                      <a href={`${JIRA_BASE_URL}/${story.key}`} target="_blank" rel="noopener noreferrer" className="text-slate-300 hover:text-indigo-600 transition-colors"><i className="fa-solid fa-up-right-from-square text-[9px]"></i></a>
                    </div>
                    <div className="flex flex-wrap gap-1 min-h-[16px]">
                      {renderTagBadges(story.tags)}
                    </div>
                    <div className="flex">
                      <span className={`text-[10px] px-2 py-0.5 rounded-md border font-bold truncate ${getStatusStyle(story.status)}`}>{story.status}</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0 py-1">
                    <h4 className="text-[14px] font-semibold text-slate-700 leading-snug group-hover:text-indigo-600 transition-colors line-clamp-2" title={story.summary}>{story.summary}</h4>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 self-center sm:self-auto">
                    {hasCache && <button onClick={() => {
                      const cachedAnalysis = getValidCache(story.key);
                      if (cachedAnalysis) {
                        setAnalysisResult({ key: story.key, content: cachedAnalysis.content, timestamp: cachedAnalysis.timestamp });
                        setShowModal(true);
                      }
                    }} className="flex items-center justify-center w-9 h-9 bg-sky-50 text-sky-600 rounded-xl hover:bg-sky-100 border border-sky-100 transition-all hover:scale-105 active:scale-95"><i className="fa-solid fa-eye text-sm"></i></button>}
                    <button onClick={() => handleSmartAnalysis(story.key)} disabled={analyzingKey === story.key} className={`flex items-center justify-center w-9 h-9 rounded-xl transition-all ${analyzingKey === story.key ? 'bg-slate-100 text-slate-300' : 'bg-amber-50 text-amber-600 hover:bg-amber-100 border border-amber-100 hover:scale-105 active:scale-95'}`}>{analyzingKey === story.key ? <i className="fa-solid fa-spinner fa-spin text-xs"></i> : <i className="fa-solid fa-wand-magic-sparkles"></i>}</button>
                  </div>
                </div>
              );
            })}
            {stories.length === 0 && !loading && (
              <div className="bg-white p-16 rounded-3xl border border-dashed border-slate-200 flex flex-col items-center gap-4 text-center">
                <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center text-slate-200">
                  <i className="fa-solid fa-ghost text-3xl"></i>
                </div>
                <div>
                  <h4 className="text-slate-800 font-bold">看板空空如也</h4>
                  <p className="text-xs text-slate-400 mt-1">点击上方“同步看板”获取最新任务数据</p>
                </div>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="flex gap-6 min-h-[500px] animate-in slide-in-from-left-4 duration-300">
          <div className="w-40 shrink-0 space-y-2">
            {isInitialLoading ? (
               <div className="animate-pulse space-y-2">
                 {[1,2].map(i => <div key={i} className="h-12 bg-slate-100 rounded-2xl w-full"></div>)}
               </div>
            ) : (
              rules.map(rule => (
                <button key={rule.id} onClick={() => setSelectedTagId(rule.id)} className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl border transition-all text-left ${selectedTagId === rule.id ? `bg-${rule.color}-50 border-${rule.color}-200 text-${rule.color}-700 shadow-sm` : 'bg-white border-slate-100 text-slate-500 hover:border-slate-200'}`}><div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-${rule.color}-100 text-${rule.color}-600`}><i className={`fa-solid ${rule.icon} text-sm`}></i></div><span className="text-sm font-black uppercase tracking-tight">{rule.tagName}</span></button>
              ))
            )}
          </div>
          {selectedRule && (
            <div className="flex-1 bg-white rounded-3xl border border-slate-200 p-8 shadow-sm flex flex-col animate-in fade-in duration-500">
              <div className="flex items-center justify-between mb-8 pb-6 border-b border-slate-50">
                <div className="flex items-center gap-4"><div className={`w-12 h-12 bg-${selectedRule.color}-50 rounded-xl flex items-center justify-center text-${selectedRule.color}-600 text-xl`}><i className={`fa-solid ${selectedRule.icon}`}></i></div><div><h3 className="text-lg font-bold text-slate-800 uppercase tracking-tight">{selectedRule.tagName} 判定规则</h3><p className="text-xs text-slate-400">{selectedRule.description}</p></div></div>
                <div className="flex flex-col items-end gap-1"><span className="text-[9px] text-emerald-600 font-bold flex items-center gap-1"><i className="fa-solid fa-server"></i>Webdis Active</span><span className="text-[8px] text-slate-300 font-mono italic">/set/{REDIS_KEY_RULES}/value</span></div>
              </div>
              <div className="flex-1 space-y-4">
                <label className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">判定逻辑集</label>
                {selectedRule.rules.map((ruleText, idx) => (
                  <div key={idx} className="group flex items-center gap-3 animate-in slide-in-from-top-1">
                    <div className="flex-none w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-400">{idx + 1}</div>
                    <input type="text" className="flex-1 bg-slate-50 border border-slate-100 rounded-xl px-4 py-2.5 text-sm text-slate-600 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all" value={ruleText} onChange={(e) => { const newRules = rules.map(r => r.id === selectedTagId ? { ...r, rules: r.rules.map((rt, i) => i === idx ? e.target.value : rt) } : r); setRules(newRules); }} placeholder="输入判定逻辑..." />
                    <button onClick={() => { setRules(rules.map(r => r.id === selectedTagId ? { ...r, rules: r.rules.filter((_, i) => i !== idx) } : r)); }} className="w-8 h-8 flex items-center justify-center text-slate-300 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"><i className="fa-solid fa-trash-can text-xs"></i></button>
                  </div>
                ))}
                <button onClick={() => { setRules(rules.map(r => r.id === selectedTagId ? { ...r, rules: [...r.rules, ''] } : r)); }} className="w-full py-3 border border-dashed border-slate-200 rounded-xl text-slate-400 hover:text-indigo-600 hover:border-indigo-300 hover:bg-indigo-50/30 transition-all text-xs font-bold flex items-center justify-center gap-2 mt-4"><i className="fa-solid fa-plus"></i>添加判定规则</button>
              </div>
              <div className="mt-8 pt-6 border-t border-slate-50 flex justify-end gap-3">
                <button onClick={loadRules} className="px-6 py-3 bg-white border border-slate-200 text-slate-500 rounded-xl font-bold text-xs hover:bg-slate-50 transition-all"><i className="fa-solid fa-rotate mr-2"></i>重置</button>
                <button onClick={saveRulesToRedis} disabled={isSaving} className="px-8 py-3 bg-indigo-600 text-white rounded-xl font-bold text-xs shadow-lg shadow-indigo-100 hover:bg-indigo-700 transition-all active:scale-95 disabled:opacity-50">{isSaving ? <><i className="fa-solid fa-spinner fa-spin mr-2"></i>正在保存...</> : <><i className="fa-solid fa-cloud-arrow-up mr-2"></i>保存至 Redis</>}</button>
              </div>
            </div>
          )}
        </div>
      )}

      {showModal && analysisResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-in fade-in" onClick={() => setShowModal(false)}></div>
          <div className="relative bg-white w-full max-w-4xl max-h-[90vh] rounded-[2.5rem] shadow-2xl flex flex-col animate-in zoom-in-95 duration-300 overflow-hidden">
            <div className="flex items-center justify-between p-7 border-b shrink-0 bg-white">
              <div className="flex items-center gap-4"><div className="w-12 h-12 bg-amber-50 rounded-2xl flex items-center justify-center text-amber-600 text-xl shadow-inner"><i className="fa-solid fa-wand-magic-sparkles"></i></div><div><h3 className="text-xl font-bold text-slate-800">智能分析报告</h3><p className="text-xs text-slate-400 font-mono tracking-tight">Jira ID: {analysisResult.key} <span className="ml-4">缓存数据获取时间: {formatTime(analysisResult.timestamp)}</span></p></div></div>
              <button onClick={() => setShowModal(false)} className="w-10 h-10 flex items-center justify-center text-slate-400 hover:bg-slate-50 rounded-full transition-colors"><i className="fa-solid fa-xmark text-xl"></i></button>
            </div>
            <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-white" dangerouslySetInnerHTML={getRenderedMarkdown(analysisResult.content)} />
            <div className="p-7 bg-slate-50 border-t flex justify-end gap-3"><button onClick={() => setShowModal(false)} className="px-8 py-3 bg-white border border-slate-200 text-slate-700 font-bold rounded-2xl text-sm hover:bg-slate-100 transition-all active:scale-95 shadow-sm">我知道了</button></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MeetingGenie;
