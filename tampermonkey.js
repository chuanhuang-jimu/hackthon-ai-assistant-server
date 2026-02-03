// ==UserScript==
// @name         Jira Story Progress Viewer (V15 - Layout Tweak)
// @namespace    http://tampermonkey.net/
// @version      15.0
// @description  Jira Story进度对比：摘要移动到标签下方，支持Markdown解析
// @author       Gemini
// @match        https://jira.veevadev.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    console.log(">>> 油猴脚本 V15 已加载: 布局调整版");

    const LOCAL_SERVER_URL = "http://127.0.0.1:8200/story/description";
    const DELAY_TIME = 600;

    // === CSS 样式配置 ===
    const CONF = {
        popupWidth: '850px',
        colTaskWidth: '300px',
        colDataWidth: '240px',
        headerHeight: '50px',
        summaryHeight: '80px',
    };

    GM_addStyle(`
        .jira-progress-popup {
            position: fixed;
            top: 50px;
            right: 20px;
            width: ${CONF.popupWidth};
            max-width: 95vw;
            max-height: 90vh;
            background: white;
            box-shadow: 0 8px 30px rgba(0,0,0,0.25);
            border-radius: 8px;
            z-index: 999999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            display: flex;
            flex-direction: column;
            border: 1px solid #dfe1e6;
            animation: slideInRight 0.3s cubic-bezier(0.2, 0, 0.2, 1);
        }

        /* 1. 标题栏 */
        .jp-header {
            padding: 0 20px;
            height: ${CONF.headerHeight};
            background: #f4f5f7;
            border-bottom: 1px solid #dfe1e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-radius: 8px 8px 0 0;
            flex-shrink: 0;
            z-index: 50;
        }
        .jp-title { font-weight: 700; color: #172b4d; font-size: 15px; }
        .jp-close {
            border: none; background: none; cursor: pointer;
            color: #6b778c; font-size: 20px; font-weight: bold;
            transition: color 0.2s;
        }
        .jp-close:hover { color: #bf2600; }

        /* 2. 标签栏 (位置调整到 Summary 上方) */
        .jp-tags-bar {
            padding: 10px 20px;
            background: #fff;
            border-bottom: 1px solid #dfe1e6;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            flex-shrink: 0;
            min-height: 0;
        }
        .jp-tags-bar:empty { padding: 0; border-bottom: none; }

        .jp-tag-item {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            box-shadow: 0 1px 2px rgba(0,0,0,0.06);
            line-height: 1.4;
        }

        .tag-style-delay { background-color: #ffebe6; color: #bf2600; border: 1px solid #ffbdad; }
        .tag-style-risk { background-color: #fff0b3; color: #172b4d; border: 1px solid #ffe380; }

        /* 3. Summary 摘要栏 (位置调整到 Tags 下方) */
        .jp-summary-box {
            height: ${CONF.summaryHeight};
            padding: 10px 20px;
            background: #fafbfc; /* 微灰背景，区分 tags 和 grid */
            border-bottom: 1px solid #dfe1e6;
            font-size: 13px;
            color: #172b4d;
            line-height: 1.6;
            overflow-y: auto;
            flex-shrink: 0;
            white-space: pre-wrap;
        }
        .jp-summary-box b { color: #0052cc; }

        /* 4. 滚动容器 */
        .jp-scroll-container {
            overflow: auto;
            flex: 1;
            position: relative;
            background: #fff;
            scroll-behavior: smooth;
        }

        .jp-grid {
            display: grid;
            grid-template-columns: ${CONF.colTaskWidth} repeat(var(--col-count), ${CONF.colDataWidth});
            width: max-content;
        }

        .jp-cell {
            padding: 12px 16px;
            border-right: 1px solid #ebecf0;
            border-bottom: 1px solid #ebecf0;
            font-size: 13px;
            line-height: 1.5;
            background: white;
            box-sizing: border-box;
            color: #172b4d;
        }

        /* === 冻结列样式 === */
        .jp-sticky-top {
            position: sticky;
            top: 0;
            z-index: 30;
            height: ${CONF.headerHeight};
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fafbfc;
            font-weight: 600;
            color: #5e6c84;
            border-bottom: 2px solid #dfe1e6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }

        .jp-sticky-left {
            position: sticky;
            left: 0;
            z-index: 20;
            border-right: 2px solid #dfe1e6;
            background: #ffffff;
        }

        .jp-sticky-corner {
            position: sticky;
            left: 0;
            top: 0;
            z-index: 40;
            height: ${CONF.headerHeight};
            display: flex;
            align-items: center;
            padding-left: 16px;
            background: #fafbfc;
            border-right: 2px solid #dfe1e6;
            border-bottom: 2px solid #dfe1e6;
            font-weight: 700;
            color: #42526e;
        }

        .jp-user-group-row {
            grid-column: 1 / -1;
            position: sticky;
            top: ${CONF.headerHeight};
            z-index: 25;
            background: #deebff;
            border-bottom: 1px solid #b3d4ff;
            border-top: 1px solid #b3d4ff;
            padding: 0;
        }

        .jp-sticky-user-name {
            position: sticky;
            left: 0;
            display: inline-flex;
            align-items: center;
            height: 100%;
            padding: 8px 16px;
            font-weight: 700;
            font-size: 13px;
            color: #0747a6;
            background: #deebff;
            min-width: ${CONF.colTaskWidth};
            box-sizing: border-box;
            border-right: 2px solid rgba(0,82,204,0.1);
        }

        .jp-task-key { color: #0052cc; font-weight: 600; display: block; margin-bottom: 6px; font-family: monospace; font-size: 12px; }
        .jp-log-item { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px dashed #ebecf0; }
        .jp-log-item:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }

        .tag-base { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .tag-worklog { color: #006644; background: #e3fcef; border: 1px solid #badcc3; }
        .tag-comment { color: #bf6c00; background: #fff0b3; border: 1px solid #ffe380; }

        .log-content { color: #253858; margin-top: 4px; white-space: pre-wrap; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", monospace; font-size: 12px; background: #fafbfc; padding: 4px; border-radius: 3px; }

        @keyframes slideInRight {
            from { transform: translateX(50px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `);

    let hoverTimer = null;
    let currentTargetLink = null;

    document.body.addEventListener('mouseover', function(event) {
        const targetLink = event.target.closest('a.ghx-parent-key');
        if (!targetLink) {
            if (currentTargetLink) {
                clearTimeout(hoverTimer);
                currentTargetLink = null;
            }
            return;
        }
        if (currentTargetLink === targetLink) return;
        const ariaLabel = targetLink.getAttribute('aria-label') || "";
        const storyId = targetLink.innerText.trim();
        if (!ariaLabel.includes("Story")) return;

        console.log(`>>> [V15] 发现 Story: ${storyId}，开始计时...`);
        clearTimeout(hoverTimer);
        currentTargetLink = targetLink;

        hoverTimer = setTimeout(() => {
            extractAndSend(targetLink, storyId);
        }, DELAY_TIME);
    });

    function extractAndSend(linkElement, storyId) {
        linkElement.style.backgroundColor = "#fff0b3";

        const timestamp = new Date().getTime();
        const fullUrl = `${LOCAL_SERVER_URL}?story_id=${encodeURIComponent(storyId)}&_t=${timestamp}`;

        GM_xmlhttpRequest({
            method: "GET",
            url: fullUrl,
            headers: { "Cache-Control": "no-cache", "Pragma": "no-cache" },
            onload: function(response) {
                if (response.status === 200) {
                    try {
                        const json = JSON.parse(response.responseText);
                        if (json.error) {
                            linkElement.style.backgroundColor = "";
                            return;
                        }
                        linkElement.style.backgroundColor = "#e3fcef";
                        renderProgressPopup(storyId, json);
                    } catch (e) {
                        console.error("JSON 解析失败", e);
                        linkElement.style.backgroundColor = "#ffebe6";
                    }
                } else {
                    linkElement.style.backgroundColor = "#ffebe6";
                }
            },
            onerror: function(err) {
                linkElement.style.backgroundColor = "#ffebe6";
            }
        });
    }

    // === 简单 Markdown 解析器 ===
    function parseMarkdown(text) {
        if (!text) return '';
        return text
            .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
            .replace(/\n/g, '<br>');
    }

    // === 核心渲染逻辑 ===
    function renderProgressPopup(storyId, responseData) {
        const old = document.querySelector('.jira-progress-popup');
        if (old) old.remove();

        // 1. 数据解析
        let processData = [];
        let tagsObj = {};
        let summaryText = "";

        if (Array.isArray(responseData)) {
            processData = responseData;
        } else {
            processData = responseData.personal_process_data || [];
            tagsObj = responseData.tags || {};
            summaryText = responseData.summary || "";
        }

        let finalTags = {};
        if (tagsObj.tags && (Array.isArray(tagsObj.tags.delay) || Array.isArray(tagsObj.tags.risk))) {
            finalTags = tagsObj.tags;
        } else {
            finalTags = tagsObj;
        }

        const delayRules = finalTags.delay || [];
        const riskRules = finalTags.risk || [];

        // 2. 数据预处理
        const allDates = [...new Set(processData.map(i => i.Date))].sort().reverse();
        const colCount = allDates.length;

        const grouped = {};
        processData.forEach(item => {
            if (!grouped[item.User]) grouped[item.User] = {};
            if (!grouped[item.User][item.Jira_ID]) {
                grouped[item.User][item.Jira_ID] = {
                    title: item.Jira_Title,
                    logsByDate: {}
                };
            }
            if (!grouped[item.User][item.Jira_ID].logsByDate[item.Date]) {
                grouped[item.User][item.Jira_ID].logsByDate[item.Date] = [];
            }
            grouped[item.User][item.Jira_ID].logsByDate[item.Date].push(item);
        });

        // 3. 构建 Tags HTML
        let tagsHtml = '';
        if (delayRules.length > 0) {
            tagsHtml += `<div class="jp-tag-item tag-style-delay">🛑 延期: ${delayRules.join('; ')}</div>`;
        }
        if (riskRules.length > 0) {
            tagsHtml += `<div class="jp-tag-item tag-style-risk">⚠️ 风险: ${riskRules.join('; ')}</div>`;
        }

        // 4. 构建 Summary HTML
        let summaryHtml = '';
        if (summaryText) {
            const formattedSummary = parseMarkdown(summaryText);
            summaryHtml = `<div class="jp-summary-box">${formattedSummary}</div>`;
        }

        // 5. 构建 UI 骨架 (调整顺序：Tags -> Summary)
        const popup = document.createElement('div');
        popup.className = 'jira-progress-popup';
        const containerWidthStyle = colCount < 3 ? 'width: auto; min-width: 600px;' : '';

        let html = `
            <div class="jp-header">
                <div class="jp-title">📋 ${storyId} 进度概览 (共 ${allDates.length} 天)</div>
                <button class="jp-close" onclick="this.closest('.jira-progress-popup').remove()">✕</button>
            </div>

            <div class="jp-tags-bar">
                ${tagsHtml}
            </div>

            ${summaryHtml}

            <div class="jp-scroll-container">
                <div class="jp-grid" style="--col-count: ${colCount}; ${containerWidthStyle}">
        `;

        // --- Grid 表头 ---
        html += `<div class="jp-cell jp-sticky-corner">任务 / 日期</div>`;
        allDates.forEach(date => {
            html += `<div class="jp-cell jp-sticky-top">${date}</div>`;
        });

        // --- Grid 内容 ---
        Object.keys(grouped).forEach(user => {
            html += `
                <div class="jp-user-group-row">
                    <div class="jp-sticky-user-name">👤 ${user}</div>
                </div>
            `;

            const userTasks = grouped[user];
            Object.keys(userTasks).forEach(jiraId => {
                const taskInfo = userTasks[jiraId];

                html += `
                    <div class="jp-cell jp-sticky-left">
                        <span class="jp-task-key">${jiraId}</span>
                        ${taskInfo.title}
                    </div>
                `;

                allDates.forEach(date => {
                    const logs = taskInfo.logsByDate[date] || [];
                    let cellContent = "";

                    if (logs.length === 0) {
                        cellContent = `<span style="color:#dfe1e6; font-size: 18px; display:block; text-align:center;">·</span>`;
                    } else {
                        logs.forEach(log => {
                            let styledContent = log.Content
                                .replace('**[Worklog', '<span class="tag-base tag-worklog">Worklog')
                                .replace('**[Comment]', '<span class="tag-base tag-comment">Comment</span>')
                                .replace('**[State Change]', '<span class="tag-base tag-worklog">State Change</span>')
                                .replace('**', '')
                                .replace(']', ']');

                            let commentHtml = '';
                            if (log.Comment) {
                                commentHtml = `<div class="log-content">${log.Comment}</div>`;
                            }

                            cellContent += `
                                <div class="jp-log-item">
                                    <div>${styledContent}</div>
                                    ${commentHtml}
                                </div>
                            `;
                        });
                    }
                    html += `<div class="jp-cell">${cellContent}</div>`;
                });
            });
        });

        html += `   </div>
                </div>`;

        popup.innerHTML = html;
        document.body.appendChild(popup);
    }
})();