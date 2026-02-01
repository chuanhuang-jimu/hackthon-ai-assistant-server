document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelectorAll('.tab-btn');
  const contents = document.querySelectorAll('.tab-content');
  
  // Tab switching logic
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      
      const targetId = tab.getAttribute('data-target');
      contents.forEach(content => {
        if (content.id === targetId) {
          content.classList.add('active');
        } else {
          content.classList.remove('active');
        }
      });
    });
  });

  // Morning Brief Logic
  const analysisTextarea = document.getElementById('analysis-textarea');
  const analysisLoading = document.getElementById('analysis-loading');

  const fetchAnalysis = () => {
    analysisTextarea.value = '正在为您分析今日日程...';
    analysisTextarea.classList.add('loading');
    analysisLoading.classList.remove('hidden');

    setTimeout(() => {
      // Mock AI response
      const mockResponse = '早上好，工程师！今天你的代码将会像诗一样优美，Bug见了你都要绕道走。如果实在躲不过，别担心，那只是生活给你加的几个小小的“断点”。祝你拥有高效而愉快的一天！';
      analysisTextarea.value = mockResponse;
      analysisTextarea.classList.remove('loading');
      analysisLoading.classList.add('hidden');
    }, 1500);
  };

  // Daily Summary Logic
  const fetchTasksBtn = document.getElementById('fetch-tasks-btn');
  const tasksTbody = document.getElementById('tasks-tbody');
  const submitContainer = document.getElementById('submit-summary-container');
  const submitBtn = submitContainer.querySelector('.submit-btn');

  const fetchLatestTasks = () => {
    fetchTasksBtn.disabled = true;
    fetchTasksBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 获取中...';
    tasksTbody.innerHTML = `
      <tr>
        <td colspan="4" class="empty-state">
          <i class="fa-solid fa-spinner fa-spin"></i> 正在从Jira同步任务...
        </td>
      </tr>
    `;

    setTimeout(() => {
      const mockTasks = [
        { id: 'PROJ-1234', title: '实现用户登录页面的视觉重构', hours: 4, notes: '已完成主要布局', url: '#' },
        { id: 'PROJ-1235', title: '修复API调用的内存泄漏问题', hours: 2.5, notes: '定位中', url: '#' },
        { id: 'PROJ-1236', title: '季度前端技术文档更新', hours: 1, notes: '进行中', url: '#' }
      ];

      tasksTbody.innerHTML = ''; // Clear loading state
      mockTasks.forEach(task => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>
            <a href="${task.url}" target="_blank">
              ${task.id}
              <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </a>
          </td>
          <td class="task-title">${task.title}</td>
          <td class="task-hours">${task.hours}h</td>
          <td class="task-notes">${task.notes}</td>
        `;
        tasksTbody.appendChild(row);
      });
      
      submitContainer.classList.remove('hidden');
      fetchTasksBtn.disabled = false;
      fetchTasksBtn.innerHTML = '<i class="fa-solid fa-rotate"></i> 获取最新信息';
    }, 1200);
  };
  
  fetchTasksBtn.addEventListener('click', fetchLatestTasks);
  submitBtn.addEventListener('click', () => {
    alert('任务进度已成功提交至系统！');
  });

  // Initial load
  fetchAnalysis();
});