
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
