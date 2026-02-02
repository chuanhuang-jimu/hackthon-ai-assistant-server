
export type AppTab = 'morning' | 'summary' | 'genie';
export type GenieSubTab = 'board' | 'tags';

export interface JiraTask {
  jira_id: string;
  sumamry: string;
  today_work_hours: string | number;
  comment: string;
  logged: string;
  remaining: string;
}

export interface JiraStory {
  key: string;
  summary: string;
  status: string;
  tags?: Record<string, string[]>; // Key 是标签名，Value 是命中规则的文本数组
}

export interface TagRule {
  id: string;
  tagName: string;
  icon: string;
  color: string;
  description: string;
  rules: string[]; // 字符串数组，用于配置管理
}

// New interface for AnalysisCache, moved from MeetingGenie.tsx
export interface AnalysisCache {
  content: string;
  expiry: number;
  timestamp: number; // Added timestamp field
}

// The BoardCache interface is also defined in MeetingGenie.tsx, let's move it too.
export interface BoardCache {
  data: JiraStory[];
  timestamp: number;
  expiry: number;
}
