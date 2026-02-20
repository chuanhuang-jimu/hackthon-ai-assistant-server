import React from 'react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  getAllWorkLogs: boolean;
  setGetAllWorkLogs: (value: boolean) => void;
  isMock: boolean;
  setIsMock: (value: boolean) => void;
  forceBatchRefresh: boolean;
  setForceBatchRefresh: (value: boolean) => void;
  userEmail: string;
  setUserEmail: (value: string) => void;
  boardId: string;
  setBoardId: (value: string) => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  getAllWorkLogs,
  setGetAllWorkLogs,
  isMock,
  setIsMock,
  forceBatchRefresh,
  setForceBatchRefresh,
  userEmail,
  setUserEmail,
  boardId,
  setBoardId,
}) => {
  const [emailInput, setEmailInput] = React.useState(userEmail);
  const [boardIdInput, setBoardIdInput] = React.useState(boardId);
  const [emailError, setEmailError] = React.useState('');

  React.useEffect(() => {
    setEmailInput(userEmail);
    setBoardIdInput(boardId);
  }, [userEmail, boardId, isOpen]);

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEmailInput(value);

    const trimmedValue = value.trim();
    const emailRegex = /^[a-zA-Z0-9._-]+@veeva\.com$/;

    if (trimmedValue === '' || emailRegex.test(trimmedValue)) {
      setUserEmail(trimmedValue);
      setEmailError('');
    } else {
      setEmailError('请输入有效的veeva.com邮箱');
    }
  };

  const handleBoardIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setBoardIdInput(value);
    setBoardId(value);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-in fade-in" onClick={onClose}></div>
      <div className="relative bg-white w-full max-w-md rounded-2xl shadow-2xl flex flex-col animate-in zoom-in-95 duration-300 overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <h3 className="text-lg font-bold text-slate-800">设置</h3>
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center text-slate-400 hover:bg-slate-100 rounded-full transition-colors">
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div className="p-6 space-y-6">
          {/* Tip/Reminder */}
          <div className="bg-amber-50 border border-amber-100 rounded-xl p-3 flex items-start gap-3">
            <i className="fa-solid fa-lightbulb text-amber-500 mt-0.5"></i>
            <p className="text-[11px] text-amber-700 leading-relaxed">
              <b>温馨提示：</b>请确保配置您真实的 <b>Veeva 邮箱</b> 和 <b>Jira 看板 ID</b>，否则数据将使用默认配置。
            </p>
          </div>

          {/* Email Input */}
          <div>
            <div>
              <p className="font-semibold text-slate-700">个人邮箱</p>
              <p className="text-xs text-slate-400">用于【晨间速览】和【今日总结】模块</p>
            </div>
            <input
              type="email"
              value={emailInput}
              onChange={handleEmailChange}
              placeholder="chuan.huang@veeva.com"
              className={`w-full mt-2 px-3 py-2 text-sm border rounded-lg outline-none transition-colors ${
                emailError
                  ? 'border-rose-500 focus:border-rose-500'
                  : 'border-slate-200 focus:border-indigo-500'
              }`}
            />
            {emailError && <p className="text-xs text-rose-500 mt-1">{emailError}</p>}
          </div>

          {/* Board ID Input */}
          <div>
            <div>
              <p className="font-semibold text-slate-700">看板ID</p>
              <p className="text-xs text-slate-400">用于【今日总结】【SCRUM MASTER】模块</p>
            </div>
            <input
              type="text"
              value={boardIdInput}
              onChange={handleBoardIdChange}
              placeholder="3485"
              className="w-full mt-2 px-3 py-2 text-sm border rounded-lg outline-none transition-colors border-slate-200 focus:border-indigo-500"
            />
          </div>

          {/* Get All Data Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-700">获取全量数据</p>
              <p className="text-xs text-slate-400">默认获取最近两日，开启后获取所有</p>
            </div>
            <button
              onClick={() => setGetAllWorkLogs(!getAllWorkLogs)}
              className={`w-12 h-6 flex items-center rounded-full px-1 transition-colors ${
                getAllWorkLogs ? 'bg-indigo-600' : 'bg-slate-200'
              }`}
            >
              <span
                className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                  getAllWorkLogs ? 'translate-x-6' : 'translate-x-0'
                }`}
              ></span>
            </button>
          </div>

          {/* Is Mock Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-700">Mock模式</p>
              <p className="text-xs text-slate-400">开启后将使用预设的模拟数据</p>
            </div>
            <button
              onClick={() => setIsMock(!isMock)}
              className={`w-12 h-6 flex items-center rounded-full px-1 transition-colors ${
                isMock ? 'bg-indigo-600' : 'bg-slate-200'
              }`}
            >
              <span
                className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                  isMock ? 'translate-x-6' : 'translate-x-0'
                }`}
              ></span>
            </button>
          </div>

          {/* Force Batch Refresh Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-700">强制一键分析</p>
              <p className="text-xs text-slate-400">开启后将忽略本地缓存，强制更新</p>
            </div>
            <button
              onClick={() => setForceBatchRefresh(!forceBatchRefresh)}
              className={`w-12 h-6 flex items-center rounded-full px-1 transition-colors ${
                forceBatchRefresh ? 'bg-indigo-600' : 'bg-slate-200'
              }`}
            >
              <span
                className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                  forceBatchRefresh ? 'translate-x-6' : 'translate-x-0'
                }`}
              ></span>
            </button>
          </div>
        </div>
        <div className="p-4 bg-slate-50 border-t flex justify-end">
          <button onClick={onClose} className="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 transition-all">
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
