
import React from 'react';

interface HeaderProps {
  onSettingsClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onSettingsClick }) => {
  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-8 z-10 shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
          <i className="fa-solid fa-bolt-lightning text-white text-xl"></i>
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-800 leading-none">工作助手·Pro</h1>
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Smart Workspace Assistant</span>
        </div>
      </div>
      
      <div className="flex items-center gap-4 text-slate-500 text-sm">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
          在线
        </div>
        <button onClick={onSettingsClick} className="hover:text-slate-800 transition-colors">
          <i className="fa-solid fa-gear"></i>
        </button>
      </div>
    </header>
  );
};

export default Header;
