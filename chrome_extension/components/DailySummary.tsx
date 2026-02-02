
import React, { useState, useEffect } from 'react';
import { JiraTask } from '../types.ts';

interface DailySummaryCache {
  tasks: JiraTask[];
  timestamp: number;
  expiry: number;
}

interface DailySummaryProps {
  getAllWorkLogs: boolean;
  isMock: boolean;
  userEmail: string;
}

const DailySummary: React.FC<DailySummaryProps> = ({ getAllWorkLogs, isMock, userEmail }) => {
  const [tasks, setTasks] = useState<JiraTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<number | null>(null);
  const [error, setError] = useState<{ message: string; isNetworkError?: boolean } | null>(null);
  
  const JIRA_BASE_URL = 'https://jira.veevadev.com/browse';
  const API_BASE_URL = 'http://127.0.0.1:8200';
  const CACHE_KEY = 'daily_summary_tasks_v1';

  const MOCK_DATA: JiraTask[] = [
    {
      jira_id: "ORI-136369",
      sumamry: "【后端】online端校验结果记录 + Ontab3个查询接口",
      today_work_hours: "",
      comment: "",
      logged: "1d 2h",
      remaining: "1d 3h"
    },
    {
      jira_id: "ORI-136366",
      sumamry: "【后端】DataModel & 框架消除逻辑",
      today_work_hours: "",
      comment: "",
      logged: "7h",
      remaining: "5h"
    }
  ];

  // 初始化加载缓存
  useEffect(() => {
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      try {
        const parsed: DailySummaryCache = JSON.parse(cached);
        if (Date.now() < parsed.expiry) {
          setTasks(parsed.tasks);
          setLastSyncTime(parsed.timestamp);
        } else {
          localStorage.removeItem(CACHE_KEY);
        }
      } catch (e) {
        localStorage.removeItem(CACHE_KEY);
      }
    }
  }, []);

  const getEndOfToday = () => {
    const now = new Date();
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
    return end.getTime();
  };

  const parseJiraTime = (timeStr: string): number => {
    if (!timeStr) return 0;
    let totalHours = 0;
    const days = timeStr.match(/(\d+)d/);
    const hours = timeStr.match(/(\d+)h/);
    const mins = timeStr.match(/(\d+)m/);

    if (days) totalHours += parseInt(days[1]) * 8;
    if (hours) totalHours += parseInt(hours[1]);
    if (mins) totalHours += parseInt(mins[1]) / 60;
    
    return totalHours || parseFloat(timeStr) || 0;
  };

  const calculateProgress = (logged: string, remaining: string) => {
    const l = parseJiraTime(logged);
    const r = parseJiraTime(remaining);
    if (l + r === 0) return 0;
    return Math.min(Math.round((l / (l + r)) * 100), 100);
  };

  const fetchLatestTasks = async (useMock = false) => {
    setLoading(true);
    setError(null);
    try {
      let rawTasks: JiraTask[] = [];

      if (useMock) {
        rawTasks = MOCK_DATA;
      } else {
        const response = await fetch(`${API_BASE_URL}/api/gemini/board/personal/task/processing`, {
          method: 'POST',
          mode: 'cors',
          headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            get_all_work_logs: getAllWorkLogs,
            mock: isMock,
            user_email: userEmail
          }), 
        });

        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
        const data = await response.json();

        if (data.success && typeof data.response === 'string') {
          rawTasks = JSON.parse(data.response);
        } else if (Array.isArray(data)) {
          rawTasks = data;
        } else {
          throw new Error("Invalid response format from server");
        }
      }

      const processedTasks = rawTasks.map(t => ({
        ...t,
        today_work_hours: t.today_work_hours === "" ? 0 : (parseFloat(String(t.today_work_hours)) || 0)
      }));

      const now = Date.now();
      const cacheData: DailySummaryCache = {
        tasks: processedTasks,
        timestamp: now,
        expiry: getEndOfToday()
      };

      setTasks(processedTasks);
      setLastSyncTime(now);
      localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));

    } catch (err: any) {
      console.error('Fetch tasks failed:', err);
      const isNetworkError = err.message === 'Failed to fetch' || err.name === 'TypeError';
      setError({
        message: isNetworkError 
          ? '无法连接到本地后端服务（127.0.0.1:8200），请检查服务状态。' 
          : err.message || '同步失败',
        isNetworkError
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTask = (jiraId: string, field: keyof JiraTask, value: string | number) => {
    const newTasks = tasks.map(task => 
      task.jira_id === jiraId ? { ...task, [field]: value } : task
    );
    setTasks(newTasks);
    
    // 自动更新缓存（保持同步）
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      try {
        const parsed: DailySummaryCache = JSON.parse(cached);
        localStorage.setItem(CACHE_KEY, JSON.stringify({ ...parsed, tasks: newTasks }));
      } catch (e) {}
    }
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

  const handleSubmit = () => {
    console.log('提交的数据:', tasks);
    alert('今日工作摘要已整理完毕！');
  };

  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-center bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-slate-800 text-sm font-bold">今日工作摘要</h2>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-slate-400 text-[11px] font-medium">自动同步个人进行中的任务进度与工时</p>
            {lastSyncTime && (
              <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-bold">
                <i className="fa-solid fa-clock-rotate-left mr-1 opacity-60"></i>
                同步时间: {formatTime(lastSyncTime)}
              </span>
            )}
          </div>
        </div>
        <button 
          onClick={() => fetchLatestTasks(false)}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shadow-md shadow-indigo-100 disabled:opacity-50"
        >
          {loading ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-arrows-rotate"></i>}
          获取最新信息
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-100 p-4 rounded-xl animate-in fade-in">
          <div className="flex items-start gap-3">
            <i className="fa-solid fa-circle-exclamation text-rose-600 mt-0.5"></i>
            <div className="flex-1">
              <p className="text-rose-600 text-xs font-bold leading-relaxed">{error.message}</p>
              {error.isNetworkError && (
                <button 
                  onClick={() => fetchLatestTasks(true)}
                  className="mt-2 text-[10px] text-rose-500 font-black uppercase tracking-widest hover:text-rose-700 underline underline-offset-4 decoration-rose-200"
                >
                  <i className="fa-solid fa-vial mr-1"></i> 使用模拟数据预览
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest w-44">Jira / Progress</th>
                <th className="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">任务标题</th>
                <th className="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center w-28">今日投入 (h)</th>
                <th className="px-4 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest w-52">进度备注</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {tasks.length > 0 ? tasks.map((task) => {
                const progress = calculateProgress(task.logged, task.remaining);
                return (
                  <tr key={task.jira_id} className="hover:bg-slate-50/50 transition-colors group">
                    <td className="px-4 py-5 align-top">
                      <div className="flex flex-col gap-3">
                        <a 
                          href={`${JIRA_BASE_URL}/${task.jira_id}`} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:text-indigo-700 font-mono font-black text-[11px] flex items-center gap-1.5 w-fit"
                        >
                          {task.jira_id}
                          <i className="fa-solid fa-up-right-from-square text-[9px] opacity-0 group-hover:opacity-100 transition-opacity"></i>
                        </a>
                        
                        <div className="space-y-1.5 max-w-[140px]">
                          <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-indigo-500 rounded-full transition-all duration-1000 shadow-[0_0_8px_rgba(99,102,241,0.3)]" 
                              style={{ width: `${progress}%` }}
                            ></div>
                          </div>
                          <div className="flex flex-col gap-0.5 font-black uppercase tracking-tighter text-[9px]">
                            <div className="flex justify-between">
                              <span className="text-slate-400">Logged:</span>
                              <span className="text-emerald-600">{task.logged || '0h'}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Remaining:</span>
                              <span className="text-amber-600">{task.remaining || '0h'}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-5 align-top">
                      <p className="text-xs font-bold text-slate-700 line-clamp-2 leading-relaxed" title={task.sumamry}>
                        {task.sumamry}
                      </p>
                    </td>
                    <td className="px-4 py-5 align-top">
                      <div className="flex justify-center">
                        <input 
                          type="number"
                          step="0.5"
                          min="0"
                          max="24"
                          value={task.today_work_hours}
                          onChange={(e) => handleUpdateTask(task.jira_id, 'today_work_hours', parseFloat(e.target.value) || 0)}
                          className="w-20 bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-100 rounded-lg px-2 py-1.5 text-xs text-center font-black text-indigo-600 outline-none transition-all"
                        />
                      </div>
                    </td>
                    <td className="px-4 py-5 align-top">
                      <div className="relative">
                        <i className="fa-solid fa-pen-to-square text-[9px] text-slate-300 absolute left-0 top-3 pointer-events-none group-focus-within:text-indigo-400 transition-colors"></i>
                        <input 
                          type="text"
                          value={task.comment}
                          placeholder="记录进度或问题..."
                          onChange={(e) => handleUpdateTask(task.jira_id, 'comment', e.target.value)}
                          className="w-full bg-transparent border-b border-transparent focus:border-indigo-200 pl-4 py-1 text-xs text-slate-600 font-medium placeholder:text-slate-300 outline-none transition-all"
                        />
                      </div>
                    </td>
                  </tr>
                );
              }) : (
                <tr>
                  <td colSpan={4} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-200">
                        <i className="fa-solid fa-clipboard-list text-2xl"></i>
                      </div>
                      <p className="text-xs text-slate-400 font-medium italic">暂无任务数据，请点击上方按钮进行同步</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {tasks.length > 0 && (
        <div className="flex justify-between items-center bg-white p-6 rounded-2xl border border-slate-200 shadow-sm animate-in slide-in-from-top-2">
          <div className="flex gap-10">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest text-center">任务总数</span>
              <span className="text-xl font-black text-slate-800 text-center">{tasks.length}</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest text-center">今日合计</span>
              <span className="text-xl font-black text-indigo-600 text-center">
                {tasks.reduce((sum, t) => sum + (Number(t.today_work_hours) || 0), 0)}
                <span className="text-xs ml-1 uppercase">h</span>
              </span>
            </div>
          </div>
          <button 
            onClick={handleSubmit}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-10 py-3.5 rounded-2xl font-black text-xs uppercase tracking-widest shadow-lg shadow-indigo-100 transition-all hover:-translate-y-0.5 active:scale-95"
          >
            确认并完成同步
          </button>
        </div>
      )}
    </div>
  );
};

export default DailySummary;
