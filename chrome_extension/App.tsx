
import React, { useState, useEffect } from 'react';
import { AppTab } from './types.ts';
import Header from './components/Header';
import MorningBrief from './components/MorningBrief';
import DailySummary from './components/DailySummary';
import MeetingGenie from './components/MeetingGenie';
import SettingsModal from './components/SettingsModal';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AppTab>('morning');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const [getAllWorkLogs, setGetAllWorkLogs] = useState(() => {
    return localStorage.getItem('getAllWorkLogs') === 'true';
  });
  const [isMock, setIsMock] = useState(() => {
    return localStorage.getItem('isMock') === 'true';
  });
  const [forceBatchRefresh, setForceBatchRefresh] = useState(() => {
    return localStorage.getItem('forceBatchRefresh') === 'true';
  });
  const [userEmail, setUserEmail] = useState(() => {
    return localStorage.getItem('userEmail') || '';
  });
  const [boardId, setBoardId] = useState(() => {
    return localStorage.getItem('boardId') || '';
  });

  useEffect(() => {
    localStorage.setItem('getAllWorkLogs', String(getAllWorkLogs));
  }, [getAllWorkLogs]);

  useEffect(() => {
    localStorage.setItem('isMock', String(isMock));
  }, [isMock]);

  useEffect(() => {
    localStorage.setItem('forceBatchRefresh', String(forceBatchRefresh));
  }, [forceBatchRefresh]);

  useEffect(() => {
    localStorage.setItem('userEmail', userEmail);
  }, [userEmail]);

  useEffect(() => {
    localStorage.setItem('boardId', boardId);
  }, [boardId]);

  return (
    <div className="flex flex-col h-screen bg-slate-50 overflow-hidden font-sans">
      <Header onSettingsClick={() => setIsSettingsOpen(true)} />
      
      {/* Tab Navigation */}
      <div className="bg-white border-b px-8 flex gap-8 shrink-0">
        {[
          { id: 'morning', label: '晨间速览', icon: 'fa-sun' },
          { id: 'summary', label: '今日总结', icon: 'fa-calendar-check' },
          { id: 'genie', label: 'Scrum Master', icon: 'fa-user-tie' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as AppTab)}
            className={`py-5 px-1 flex items-center gap-2 border-b-2 transition-all font-bold text-xs uppercase tracking-widest ${
              activeTab === tab.id 
                ? 'border-indigo-600 text-indigo-600' 
                : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            <i className={`fa-solid ${tab.icon} ${activeTab === tab.id ? 'animate-pulse' : ''}`}></i>
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Main Content Area - Keep components alive using display: none */}
      <main className="flex-1 overflow-y-auto p-8 custom-scrollbar">
        <div className="max-w-5xl mx-auto">
          <div style={{ display: activeTab === 'morning' ? 'block' : 'none' }}>
            <MorningBrief />
          </div>
          <div style={{ display: activeTab === 'summary' ? 'block' : 'none' }}>
            <DailySummary getAllWorkLogs={getAllWorkLogs} isMock={isMock} userEmail={userEmail} />
          </div>
          <div style={{ display: activeTab === 'genie' ? 'block' : 'none' }}>
            <MeetingGenie getAllWorkLogs={getAllWorkLogs} isMock={isMock} forceBatchRefresh={forceBatchRefresh} />
          </div>
        </div>
      </main>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        getAllWorkLogs={getAllWorkLogs}
        setGetAllWorkLogs={setGetAllWorkLogs}
        isMock={isMock}
        setIsMock={setIsMock}
        forceBatchRefresh={forceBatchRefresh}
        setForceBatchRefresh={setForceBatchRefresh}
        userEmail={userEmail}
        setUserEmail={setUserEmail}
        boardId={boardId}
        setBoardId={setBoardId}
      />
    </div>
  );
};

export default App;
