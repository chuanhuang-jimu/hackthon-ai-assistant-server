import re
import json
import asyncio
from redis_utils import query_redis, set_redis, async_query_redis, async_set_redis

# 原始 Markdown 数据
markdown_data = "## 🚁 Plum 25R3.2 Sprint 2 : ORI-114277 整体进展综述\n> **当前状态**: QA In Progress | **整体进度**: 4/11\n> **风险提示**: 🟠 进度滞后\n\n**📝 最新情况摘要**:\nStory 主要研发工作已完成并转入测试阶段。过去两天，开发人员 Garry Peng 集中处理了三个相关的子任务/缺陷，并记录了 3.5 小时工时，主要解决了多个富文本字段在特定场景下的显示和值清空问题。QA 负责人 Zijie Tang 已开始介入，并要求提供用于PS代码自定义逻辑的Demo数据。\n\n---\n\n## 👥 团队成员详细动态 (过去两天)\n\n### 👤 Chuan Huang\n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Comment]** [~garry.peng@veeva.com] feature/ORI-136135/admin-affect-others-support-long-text\n上面分支加上了\n\n### 👤 Garry Peng\n\n#### 🔹 ORI-136183 【admin】 longtext 字段为文本类型时，配置字段影响关系页面，在关联字段配置固定值处输入带标签的内容，在预览页面会变成富文本的样式 ([🔵 task])\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136135 【admin】longtext 字段在初始拖入页面时，设置关联字段的固定值输入框，没有展示富文本样式 ([🔵 task])\n* **2026-01-22**:\n    * **[Worklog 30m]** \n    * **[Comment]** /admin-api/object/\\{object_id}/page-layout/\\{layout_id}/ 接口返回的 all_fields 中的字段也需要带上 text_type [~chuan.huang@veeva.com] \n\n!image-2026-01-22-17-37-48-539.png!\n* **2026-01-23**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Worklog 1h 30m]** \n\n### 👤 Zijie Tang\n\n#### 🔹 ORI-136130 【online】 控制字段将longtext 字段 带入值后，再将控制字段的值清空，longtext 字段的值未清空 ([🔴 defect])\n* **2026-01-22**:\n    * **[Comment]** wechat 端同样存在这个问题\n\n---\n*注：报表生成时间 2026-01-24*"
markdown_data_1 = """## 🚁 Plum 25R3.3 Sprint 2 : ORI-132922 整体进展综述\n> **当前状态**: Development in Progress | **整体进度**: 5/12\n> **风险提示**: 无风险\n\n**📝 最新情况摘要**:\n根据现有数据，Story 整体处于开发中状态，无高优风险。最近的动态是 2026-02-14 相关人员就 snapshot 数据的更新与消除逻辑进行了讨论和确认，表明团队正在积极解决业务流程中的技术细节。前端与后端开发任务均有持续进展。\n\n---\n\n## 👥 团队成员详细动态 (全量历史)\n\n*(仅展示有数据的成员)*\n\n### 👤 Chuan Huang\n\n#### 🔹 ORI-136371 【后端】联调 (🔵 task)\n* **[2026-02-10]**:\n    * **[Worklog 2h]** \n    * **[Worklog 3h]** \n\n#### 🔹 ORI-136369 【后端】online端校验结果记录 + Ontab3个查询接口 (🔵 task)\n* **[2026-01-29]**:\n    * **[Worklog 5h]** 校验记录快照存储\n* **[2026-01-30]**:\n    * **[Worklog 5h]** 业务 前后端一起核对 adv-tab交互流程 和Garry确定on-tab查询接口出入参\n* **[2026-02-02]**:\n    * **[Worklog 3h]** \n* **[2026-02-05]**:\n    * **[Worklog 1h]** 投入较少 和 业务对了一下持久化数据格式 针对多summary的场景再微调一下\n    * **[Worklog 4h]** 分拣存储 & 分tab查询接口开发完成 还剩risk区分接口\n* **[2026-02-10]**:\n    * **[Worklog 3h]** 遗留代码处理\n\n#### 🔹 ORI-136366 【后端】DataModel & 框架消除逻辑 (🔵 task)\n* **[2026-01-26]**:\n    * **[Worklog 5h]** \n* **[2026-01-27]**:\n    * **[Worklog 2h]** \n* **[2026-02-05]**:\n    * **[Worklog 3h]** datamodel调整 & 失效逻辑提交\n* **[2026-02-09]**:\n    * **[Worklog 2h]** 软提示记录改造到后端\n\n#### 🔹 ORI-136186 【后端】on-tab开发 (🔵 task)\n* **[2026-01-26]**:\n    * **[Worklog 3h]** model处理\n    * **[Comment]** 单独拆分子任务\n\n#### 🔹 ORI-135338 【后端】实现前置调研 (🔵 task)\n* **[2026-01-13]**:\n    * **[Worklog 3m]** \n    * **[Worklog 3h]** \n* **[2026-01-14]**:\n    * **[Worklog 2h]** \n* **[2026-01-15]**:\n    * **[Worklog 3h]** \n* **[2026-01-16]**:\n    * **[Worklog 5h]** \n* **[2026-01-19]**:\n    * **[Worklog 5h]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-20]**:\n    * **[Comment]** 01.20 on-tab和业务后端的交互沟通了，平台后端预计5point 当前现状下多对象触发 提示信息不准的问题还没有明确解决方案，我今天会约架构师一起讨论明确一下方案，这个问题修复预计会增加2point开发工作量 01.19 昨天和业务产品技术一起确定了 产品demo的一些业务细节，01.20会拉技术一起确定两边技术交互的细节，然后可以定排期开发\n* **[2026-01-21]**:\n    * **[Comment]** * 后端BR-OnTab场景  ** BR框架支持 本次ontab数据 消除&存储&业务后端交互 【2】  ** on-Tab的前端校验写入接口 【1】  ** Tab信息聚合查询接口【1】  ** 智能建议依赖数据查询【1】  ** 原disregards接口改造【0.5】 * 联调：2 * V2 多对象场景，跨对象提示信息消除不准问题解决【2】这个感觉可以单独story\n* **[2026-02-02]**:\n    * **[Comment]** 上周五 event侧 同步policy-helper需求有变动，产品最新设计与br-onTab的交互有冲突，目前和产品以及manager沟通暂时先hold住 cc [~garry.peng@veeva.com] [~yi.yang@veeva.com] [~howie.peng@veeva.com] [~rui.zeng@veeva.com] [~jie.zhou@veeva.com]\xa0\n    * **[Comment]** 目前周一上午和杨易最新沟通，后端先正常开发，后端和[~garry.peng@veeva.com] 会先开发 提示信息记录 + 分tab查询部分功能，risk区域平台UI（不含智能建议 + 非BR risk提示混合展示）等[~yi.yang@veeva.com]提供 前端智能建议整体样式部分等[~yi.yang@veeva.com] 周二和客户沟通后有最新结论后同步我们\n    * **[Comment]** [~garry.peng@veeva.com] \xa0 【快照记录入参】 {code:java} 取v2的数据结构转json即可  {"event": {"390": {"66": {"trigger_ins": {"object_name": "event", "record_id": 390}, "rule_id": 66, "latest_comment": "\\u8df3\\u8fc7", "is_hard_stop": false, "comment_required_on_bypass": true, "check_point_name": null, "summary": [{"message": "<p>\\u5b58\\u5728<veev-exp>2</veev-exp>&#8203;\\u4f4d\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0\\u7684\\u53c2\\u4f1a\\u4eba</p>", "trigger_ins": {"object_name": "event", "record_id": 390}, "is_hard_stop": false, "comment_required_on_bypass": true, "extra_info": {}, "details": [{"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>\\u9ec4\\u5b87\\u5149</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "trigger_ins": {"object_name": "event", "record_id": 390}, "extra_info": {}, "msg_info": {"custombr_86ro8R0VC": {"e1": "\\u9ec4\\u5b87\\u5149"}}, "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [313]}}}, {"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>Allen.Luo</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "trigger_ins": {"object_name": "event", "record_id": 390}, "extra_info": {}, "msg_info": {"custombr_86ro8R0VC": {"e1": "Allen.Luo"}}, "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [315]}}}], "msg_info": {"custombr_86ro8QU2A": {"e1": "2"}}, "message_key": "cs_summary_key", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {}}}]}}}}{code} 【on-tab接口】 {code:java} 入参 {"search_object_name":"event","search_object_record_id":389,"page_layout_id":"d47fd211-45ae-464d-af76-1ed792057bee","front_advanced_layout_tab_mapping":{"event_attendee":["event_account","event_professional","contact","event_speaker"],"tab_name2":["realted_name_3"]}} 返回 \xa0{"event_attendee":[[{"message":"&lt;p&gt;存在&lt;veev-exp&gt;2&lt;/veev-exp&gt;&amp;#8203;位不允许参加的参会人&lt;/p&gt;","message_key":"cs_summary_key","persistence_config":{"search_object_name":"event","search_object_record_id":389,"related_objects":{}},"details":[{"message":"&lt;p&gt;参会人&lt;veev-exp&gt;李大魁&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":389,"related_objects":{"event_account":[305]}}},{\\"message":"&lt;p&gt;参会人&lt;veev-exp&gt;李强&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":389,"related_objects":{"event_account":[306]}}}],"ai_suggestion":{"content":"将xxx医生替换为符合科室规范的参会医生","type":"text"}}],[{"message":"&lt;p&gt;存在&lt;veev-exp&gt;2&lt;/veev-exp&gt;&amp;#8203;位不允许参加的参会人&lt;/p&gt;","message_key":"cs_summary_key","persistence_config":{"search_object_name":"event","search_object_record_id":390,"related_objects":{}},"details":[{"message":"&lt;p&gt;参会人&lt;veev-exp&gt;黄宇光&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":390,"related_objects":{"event_account":[313]}}},{\\"message":"&lt;p&gt;参会人&lt;veev-exp&gt;Allen.Luo&lt;/veev-exp&gt;&amp;#8203;不允许参加&lt;/p&gt;","message_key":"cs_summary_key_detail","persistence_config":{"search_object_name":"event","search_object_record_id":390,"related_objects":{"event_account":[315]}}}],"ai_suggestion":null}]]}{code}\n* **[2026-02-05]**:\n    * **[Comment]** [~pisheng.zhong@veeva.com] [~haohao.ji@veeva.com] [~yidi.yang@veeva.com]\xa0 {code:java} br_check_snapshot.msg 分拣后的校验结果 uniq_key = rule_id + trigger_object_id + trigger_object_name [{"message": "<p> \xa0\\u5b58\\u5728<veev-exp>2</veev-exp>&#8203;\\u4f4d\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0\\u7684\\u53c2\\u4f1a\\u4eba</p>", "message_key": "cs_summary_key", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {}}, "details": [{"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>\\u9ec4\\u5b87\\u5149</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [313]}}}, {"message": "<p>\\u53c2\\u4f1a\\u4eba<veev-exp>Allen.Luo</veev-exp>&#8203;\\u4e0d\\u5141\\u8bb8\\u53c2\\u52a0</p>", "message_key": "cs_summary_key_detail", "persistence_config": {"search_object_name": "event", "search_object_record_id": 390, "related_objects": {"event_account": [315]}}}]}]  智能建议 数据结构 { \xa0 \xa0 "ai_suggestion": { \xa0 \xa0 \xa0 \xa0 "cs_summary_key": { \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "content": "将xxx医生替换为符合科室规范的参会医生", \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "type": "text" \xa0 \xa0 \xa0 \xa0 }, \xa0 \xa0 \xa0 \xa0 "cs_summary_key_2": { \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "content": "", \xa0 \xa0 \xa0 \xa0 \xa0 \xa0 "type": "markdown" \xa0 \xa0 \xa0 \xa0 } \xa0 \xa0 } }{code} \xa0  \xa0\n* **[2026-02-13]**:\n    * **[Comment]** 硬提示的校验 如果要记录，记录的结果 必须 要和当前的数据状态保持一致，只举一个 数据校验后触发硬提示场景（可能实际业务上没有） 1. 比如 开始开会 按钮，用户将会议状态从草稿 改为 进行中，({color:#de350b}举例可能不太合适，我们只是在一次button行为中找一个数据变更触发的硬提示文案和当前数据状态不一致的场景{color})，在post_save中触发了硬提示，提示 进行中的会议，费用不能超过2000，点击去修改后会把提示记录下来 但是当前会议的状态还是草稿中，我们记录的硬提示 是在 描述 数据变更后的提示，会有和当前数据状态不一致的风险 [~yi.yang@veeva.com]\xa0 我这边暂时找不到真实的业务场景，按照刚刚的沟通，我们也可以假设不会存在这种场景（一个button在点击后修改了数据 并 触发了BR硬提示描述说明了变更后的内容，我们做了记录 但是数据还是变更前的），不对此场景做处理 或者后续发现了这种场景，我们推动客户去修改文案，让文案不和修改的数据内容有关联尽量避免歧义\n\n### 👤 Garry Peng\n\n#### 🔹 ORI-136367 【前端】功能实现 (🔵 task)\n* **[2026-01-29]**:\n    * **[Worklog 2h]** \n    * **[Worklog 1h]** 接口方案对齐\n    * **[Worklog 2h]** \n* **[2026-02-06]**:\n    * **[Worklog 1h 30m]** \n* **[2026-02-09]**:\n    * **[Worklog 2d 1h]** \n    * **[Worklog 30m]** \n* **[2026-02-10]**:\n    * **[Worklog 2h 30m]** \n    * **[Worklog 4h]** \n* **[2026-02-12]**:\n    * **[Worklog 3h 30m]** \n* **[2026-02-13]**:\n    * **[Worklog 3h]** \n\n#### 🔹 ORI-135337 【前端】调研 (🔵 task)\n* **[2026-01-13]**:\n    * **[Worklog 5h 30m]** \n    * **[Comment]** h1. 数据记录 *记录时机* 软提示br弹窗点击继续按钮时 *方案* 服务端增加一个数据记录接口 在br弹窗 trigger-dialog 的 handleContinue 函数中调用接口 \xa0 修改范围：wechat，web2 \xa0\n    * **[Comment]** h1. Tab 提示 !image-2026-01-13-14-50-14-119.png! \xa0 在页面加载阶段获取数据（调用接口） h2. Online 端 *web2*\xa0 page-layout-facade.vue h2. Wechat 端 *wechat* pl-view.html \xa0\n    * **[Comment]** h1. 消息提示区域 *需求* * 增加开关字段，用于控制是否展示新版ui * 新版 ui：智能合规提示，提示信息包含新版合规提示信息和 disregard 数据；用户自定义的提示信息展示在 risk info 区域 * 旧版 ui：disregard 数据和客户自定义提示数据一起展示在 risk info 区域 *方案* * /api/business-rule-disregards/\xa0 接口改造： ** 新增一个参数（参数名待定），bool 类型 ** true：返回 disregard 数据 + 用户自定义数据；false：只返回用户自定义数据 * 前端增加智能合规提示组件 \xa0 *web2:* page-layout-facade.vue {code:java} <router-view v-slot="{ Component }"> ... \xa0 \xa0<div class="tab-collapse-content"> <智能合规提示 /> \xa0 \xa0 \xa0 \xa0<component :is="Component" ... /> </div> ... </router-view>{code} tab-wrapper.vue {code:java} <template> <div> <智能合规提示 /> <component :is="resolvedTemplate" :meta="meta" :data="data" :parent-ctrl="pageCtrl"> </component> </div> </template> {code} *wechat* pl-view.html {code:java} <div class="page-body"> \xa0 \xa0<智能合规提示 /> </div> {code} {code:java} <uib-tab ng-repeat="tabItem in pageCtrl.tabs" ...> <智能合规提示 /> </uib-tab>{code} 智能合规提示组件 !image-2026-01-13-18-22-25-769.png! approval-warning 组件改造 h2. !image-2026-01-13-18-24-49-723.png! \xa0 \xa0 \xa0\n* **[2026-01-14]**:\n    * **[Worklog 1h]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-21]**:\n    * **[Comment]** 前端点数拆分： * br 弹窗调整【1】 ** 写数据 ** 根据br类型区分行为（checkpoint类型和 button 类型表现不同） * tab 展示提示 icon （wechat 和 online 双端，2个技术栈）【2】 * 智能提示组件\xa0 ** 公共组件（wechat 和 online 双端）【2】 ** 数据更新流程调研+实现【1】 * risk 区域组件调整 【1】 ** 根据 custom setting 开关切换数据源 * 联调 + 自测【2】\n* **[2026-01-29]**:\n    * **[Comment]** h2. 交互流程图 [https://gvpp34oja7w.feishu.cn/docx/RH5fd4DrsoCgTxxHMMxchWnfnbh?blockId=TuHTdoHUfoHCw6xg0EycnUEDn9f&blockToken=ARfMwQ09mhriLZblsFxcpRpynCb&blockType=whiteboard&doc_app_id=501]\n* **[2026-02-03]**:\n    * **[Comment]** 接口地址\xa0 [http://\\{{host}}/api/business-rule-v2/record-br-check-snapshot] [http://\\{{host}}/api/business-rule-v2/validation-results] \xa0 \xa0 \xa0\n* **[2026-02-11]**:\n    * **[Comment]** 点击【去修改】按钮记录 snapshot： 在 view 页面记录，在 layout 页面不记录 只判断是否是 view 页面，不区分按钮。 即：无论哪个按钮，只要是在 view 页面触发了br弹窗，点击去修改，都会调用记录 snapshot 的接口 cc [~jie.zhou@veeva.com] [~yi.yang@veeva.com] \xa0[~chuan.huang@veeva.com]\xa0\n\n### 👤 Jie Zhou\n\n#### 🔹 ORI-135329 测试用例 (🔵 task)\n* **[2026-01-29]**:\n    * **[Worklog 1d 1h]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-07]**:\n    * **[Comment]** 豁免 bug 改了以后： 点继续-回到 view 页面，只有 v2 的情况下，也会弹多次软提示框 check_business_rale_result： * identify 和 process !image-2026-01-07-16-58-58-491.png|width=592,height=144! 要看下这个场景\n    * **[Comment]** 1、期望的是 哪个对象 br 报错，点继续，就跳转到哪个 tab。如果不能实现，就跳转到基本信息页 2、需要考虑只有详情页，触发 br 的情况，没有「基本信息」title，也不会有小红点，只会有 risk info 3、 会议取消： \xa0pagelayout view 页面-点会议取消-硬提示 - 去修改 - 第一个报错的 tab \xa0pagelayout view 页面-点会议取消-软提示 - 继续 -\xa0 取消成功 -跳到 view 页面 \xa0 保存场景： 保存-硬提示 - 去修改 - 跳到edit 页面 保存-软提示 - 继续 - 保存成功 -跳到 view 页面 !image-2026-01-07-17-24-36-920.png|width=573,height=321! 不同接口 点继续-identify接口-记录了 brd 和小红点，点取消，回来显示 brd 和小红点 点确定-process接口-又调了一次 br，会显示临时增加的 rule（点继续之后增加的） \xa0 历史数据能不能支持有小红点？ \xa0 去修改 \xa0-- \xa0修改前的一个建议 \xa0不是 brd \xa0 \xa0 新表 \xa0 \xa0父集\xa0\xa0 继续 \xa0--- \xa0数据保存了，记录的 brd \xa0 子集 \xa0客户拿去做审计 \xa0\n    * **[Comment]** 调研： 前端：2\xa0 tab 组件、AI 提示 UI 后端：2 QA：7\n* **[2026-01-16]**:\n    * **[Comment]** 0116 早会： 调研需要去了解业务的东西 * 细节处理和 trigger 实现强相关 * 一些交互在 refine 上没有聊到\n\n### 👤 Rui Zeng\n\n#### 🔹 ORI-135337 【前端】调研 (🔵 task)\n* **[2026-01-26]**:\n    * **[Worklog 5h 30m]** \n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-01-21]**:\n    * **[Comment]** 0121 早会 预估点数： B : 7.5 F: 9 \xa0\n\n### 👤 Yi Yang\n\n#### 🔹 ORI-132922 【BR V2】BR v2 提示信息 on-tab（2.24） (🔵 task)\n* **[2026-02-14]**:\n    * **[Comment]** \xa0业务流程上，对应“ 一旦snapshot 数据更新（view 页面的去修改+继续按钮，edit 页面的 继续按钮），则需要执行消除操作 ” ---- 补充： 平台提供的功能是：一旦snapshot 数据更新，则去执行消除操作 若业务层、或者ps的特殊业务逻辑（主要是更新数据），或者 br msg 的描述问题（记录 + 消除），引发了用户的confuse，那么需要更改 br 文案，或者调整 业务层、或者ps的数据更新逻辑\n\n---\n*注：报表生成时间 2026-02-20*"""


def parse_to_json(text, story_id):
    """
    解析Markdown并将结果保存/合并到指定Sprint和Story的文件中。
    Sprint ID 会从 text 的第一行标题中自动提取。
    """

    # ---------------------------------------------------------
    # 0. 提取 Sprint ID
    # ---------------------------------------------------------
    sprint_match = re.search(r'^##\s+\S+\s+(.*?)\s*:', text, re.MULTILINE)

    if sprint_match:
        sprint_id = sprint_match.group(1).strip()
        print(f"检测到 Sprint ID: {sprint_id}")
    else:
        sprint_id = "Unknown_Sprint"
        print("Warning: 未能从文本中提取 Sprint ID，使用默认值。")

    # ---------------------------------------------------------
    # 1. 提取并存储“最新情况摘要”
    # ---------------------------------------------------------
    summary_match = re.search(r'(\*\*📝 最新情况摘要\*\*:\n.*?)---', text, re.DOTALL)
    if summary_match:
        summary_content = summary_match.group(1).strip()
        summary_redis_key = f"story:summary:{story_id}"
        set_redis(summary_redis_key, summary_content)
        print(f"成功提取“最新情况摘要”并存入 Redis (Key: {summary_redis_key})。")
    else:
        print("Warning: 未能在文本中找到“最新情况摘要”部分。")

    # ---------------------------------------------------------
    # 2. 核心解析逻辑
    # ---------------------------------------------------------
    lines = text.split('\n')
    new_parsed_data = []

    current_user = None
    current_jira_id = None
    current_jira_title = None
    current_date = None

    # 更加精准的正则匹配
    # 用户：必须恰好是 3 个井号，后面不能跟井号
    re_user = re.compile(r'^#{3}(?!#)\s*.*?👤?\s*(.+)')
    # Jira：必须恰好是 4 个井号，后面不能跟井号
    re_jira = re.compile(r'^#{4}(?!#)\s*.*?🔹?\s*(ORI-\d+)\s*(.*)')
    # 日期：支持多种格式，包括带星号和不带星号
    re_date = re.compile(r'^\*?\s*\*\*\[?(\d{4}-\d{2}-\d{2})\]?\*\*:?')
    # Item：匹配缩进的列表项
    re_item = re.compile(r'^\s+\*\s+(\*\*\[.*?\]\*\*)\s*(.*)')

    for line in lines:
        stripped_line = line.strip()
        
        # 1. 优先匹配 Jira ID (Level 4 Header)
        jira_match = re_jira.match(stripped_line)
        if jira_match:
            current_jira_id = jira_match.group(1).strip()
            current_jira_title = jira_match.group(2).strip()
            continue

        # 2. 匹配用户 (Level 3 Header)
        user_match = re_user.match(stripped_line)
        if user_match:
            current_user = user_match.group(1).strip()
            continue

        # 3. 匹配日期
        date_match = re_date.match(stripped_line)
        if date_match:
            current_date = date_match.group(1).strip()
            continue

        # 4. 匹配具体事项 (注意：这里使用原 line，因为需要判断行首缩进)
        item_match = re_item.match(line)
        if item_match:
            tag_part = item_match.group(1)
            text_part = item_match.group(2)

            # 只有在 User, Jira ID, Date 都已确定的情况下才记录数据
            if current_user and current_jira_id and current_date:
                new_parsed_data.append({
                    "User": current_user,
                    "Jira_ID": current_jira_id,
                    "Jira_Title": current_jira_title,
                    "Date": current_date,
                    "Content": tag_part,
                    "Comment": text_part.strip()
                })

    # ---------------------------------------------------------
    # 3. Redis 操作逻辑
    # ---------------------------------------------------------

    # 构造 Redis Key, 格式: story:personal_progress:{story_id}
    redis_key = f"story:personal_progress:{story_id}"

    # 从 Redis 读取现有数据
    existing_data = query_redis('GET', redis_key)
    if not isinstance(existing_data, list):
        final_data = []
    else:
        final_data = existing_data
    
    print(f"从 Redis (Key: {redis_key}) 读取了 {len(final_data)} 条已有数据。")

    # 数据清理与合并逻辑
    
    # 1. 清理 Redis 中的现有脏数据（去重）
    initial_count = len(final_data)
    
    # 使用字典去重，保留每个复合键最后出现的元素。
    # 这一步同时也为后续合并 new_parsed_data 准备了 existing_map。
    existing_map = {
        (item.get('User'), item.get('Jira_ID'), item.get('Date')): item
        for item in final_data if isinstance(item, dict) and all(item.get(k) for k in ['User', 'Jira_ID', 'Date'])
    }
    final_data = list(existing_map.values())
    
    cleaned_count = len(final_data)
    if initial_count > cleaned_count:
        print(f"数据清理：检测到并移除了 {initial_count - cleaned_count} 条重复的现有记录。")

    # 2. 将新解析的数据合并到已清理的数据中
    update_count = 0
    append_count = 0

    for new_item in new_parsed_data:
        # 确保 new_item 格式正确
        if not (isinstance(new_item, dict) and all(new_item.get(k) for k in ['User', 'Jira_ID', 'Date'])):
            continue
            
        key = (new_item['User'], new_item['Jira_ID'], new_item['Date'])
        existing_item = existing_map.get(key)

        if existing_item:
            # 键存在，更新
            if existing_item.get('Content') != new_item.get('Content') or existing_item.get('Comment') != new_item.get('Comment'):
                existing_item.update(new_item)
                update_count += 1
        else:
            # 键不存在，新增
            final_data.append(new_item)
            existing_map[key] = new_item
            append_count += 1

    # 3. 结果写回
    # 只要有任何变动（清理、新增、更新），就执行写回操作
    if initial_count != cleaned_count or append_count > 0 or update_count > 0:
        if append_count > 0:
            print(f"成功追加 {append_count} 条新记录。")
        if update_count > 0:
            print(f"成功更新 {update_count} 条现有记录。")
        
        set_redis(redis_key, final_data)
        print(f"数据已写回 Redis (Key: {redis_key})。")
    else:
        print("无需改动：数据已是最新且无重复。")

    return final_data


async def async_parse_to_json(text, story_id):
    """
    异步解析Markdown并将结果保存/合并到指定Sprint和Story的文件中。
    """
    sprint_match = re.search(r'^##\s+\S+\s+(.*?)\s*:', text, re.MULTILINE)

    if sprint_match:
        sprint_id = sprint_match.group(1).strip()
    else:
        sprint_id = "Unknown_Sprint"

    summary_match = re.search(r'(\*\*📝 最新情况摘要\*\*:\n.*?)---', text, re.DOTALL)
    if summary_match:
        summary_content = summary_match.group(1).strip()
        summary_redis_key = f"story:summary:{story_id}"
        await async_set_redis(summary_redis_key, summary_content)

    lines = text.split('\n')
    new_parsed_data = []
    current_user = None
    current_jira_id = None
    current_jira_title = None
    current_date = None

    re_user = re.compile(r'^#{3}(?!#)\s*.*?👤?\s*(.+)')
    re_jira = re.compile(r'^#{4}(?!#)\s*.*?🔹?\s*(ORI-\d+)\s*(.*)')
    re_date = re.compile(r'^\*?\s*\*\*\[?(\d{4}-\d{2}-\d{2})\]?\*\*:?')
    re_item = re.compile(r'^\s+\*\s+(\*\*\[.*?\]\*\*)\s*(.*)')

    for line in lines:
        stripped_line = line.strip()
        
        jira_match = re_jira.match(stripped_line)
        if jira_match:
            current_jira_id = jira_match.group(1).strip()
            current_jira_title = jira_match.group(2).strip()
            continue
            
        user_match = re_user.match(stripped_line)
        if user_match:
            current_user = user_match.group(1).strip()
            continue
            
        date_match = re_date.match(stripped_line)
        if date_match:
            current_date = date_match.group(1).strip()
            continue
            
        item_match = re_item.match(line)
        if item_match:
            tag_part = item_match.group(1)
            text_part = item_match.group(2)
            if current_user and current_jira_id and current_date:
                new_parsed_data.append({
                    "User": current_user,
                    "Jira_ID": current_jira_id,
                    "Jira_Title": current_jira_title,
                    "Date": current_date,
                    "Content": tag_part,
                    "Comment": text_part.strip()
                })

    redis_key = f"story:personal_progress:{story_id}"
    existing_data = await async_query_redis('GET', redis_key)
    
    if not isinstance(existing_data, list):
        final_data = []
    else:
        final_data = existing_data

    existing_map = {
        (item.get('User'), item.get('Jira_ID'), item.get('Date')): item
        for item in final_data if isinstance(item, dict) and all(item.get(k) for k in ['User', 'Jira_ID', 'Date'])
    }
    
    update_count = 0
    append_count = 0

    for new_item in new_parsed_data:
        if not (isinstance(new_item, dict) and all(new_item.get(k) for k in ['User', 'Jira_ID', 'Date'])):
            continue
        key = (new_item['User'], new_item['Jira_ID'], new_item['Date'])
        existing_item = existing_map.get(key)
        if existing_item:
            if existing_item.get('Content') != new_item.get('Content') or existing_item.get('Comment') != new_item.get('Comment'):
                existing_item.update(new_item)
                update_count += 1
        else:
            final_data.append(new_item)
            existing_map[key] = new_item
            append_count += 1

    if len(existing_data) != len(final_data) or append_count > 0 or update_count > 0:
        await async_set_redis(redis_key, final_data)

    return final_data


def get_story_description(story_id):
    # 1. Get personal progress data
    personal_progress_key = f"story:personal_progress:{story_id}"
    personal_process_data = query_redis('GET', personal_progress_key)

    # 2. Get tags data
    tags_key = f"story:tags:{story_id}"
    tags_data = query_redis('GET', tags_key)

    # 3. Get summary data
    summary_key = f"story:summary:{story_id}"
    summary_data = query_redis('GET', summary_key)

    # If all are missing, return an error
    if not personal_process_data and not tags_data and not summary_data:
        return {"error": f"在 Redis 中未找到 story '{story_id}' 的任何相关数据（进度、标签或综述）。"}

    # 4. Combine into the final dictionary
    result = {
        "summary": summary_data if summary_data else "",
        "tags": tags_data if tags_data else [],
        "personal_process_data": personal_process_data if personal_process_data else []
    }

    return result


async def async_get_story_description(story_id):
    # 1. 获取个人进度数据 (Key: story:personal_progress:{story_id})
    personal_progress_key = f"story:personal_progress:{story_id}"
    personal_process_data = await async_query_redis('GET', personal_progress_key)

    # 2. 获取标签数据 (Key: story:tags:{story_id})
    tags_key = f"story:tags:{story_id}"
    tags_data = await async_query_redis('GET', tags_key)

    # 3. 获取综述数据 (Key: story:summary:{story_id})
    summary_key = f"story:summary:{story_id}"
    summary_data = await async_query_redis('GET', summary_key)

    # 容错处理：只要其中任何一项有值，就认为成功
    has_data = any([
        personal_process_data and len(personal_process_data) > 0,
        tags_data,
        summary_data
    ])

    if not has_data:
        return {
            "summary": "",
            "tags": {"delay": [], "risk": []},
            "personal_process_data": [],
            "warning": f"未找到 story '{story_id}' 的有效追踪数据，请确保已执行过 story_check。"
        }

    # 4. 组合最终结果
    result = {
        "summary": summary_data if summary_data else "暂无综述信息",
        "tags": tags_data if tags_data else {"delay": [], "risk": []},
        "personal_process_data": personal_process_data if personal_process_data else []
    }

    return result


# --- 测试调用 ---
if __name__ == "__main__":
    async def main_test():
        try:
            # 同步调用
            # result = parse_to_json(markdown_data_1, story_id="ORI-114277")
            
            # 异步调用
            result = await async_parse_to_json(markdown_data_1, story_id="ORI-132922")

            print(f"\n最终数据条数: {len(result)}")
            if len(result) > 0:
                print("预览第一条数据:")
                print(json.dumps(result[:1], indent=2, ensure_ascii=False))
            else:
                print("警告: 结果为空，请检查 Regex 匹配逻辑或输入数据上下文。")
            
            print("\n--- Testing story_description ---")
            story_data = await async_get_story_description("ORI-114277")
            print(json.dumps(story_data, indent=2, ensure_ascii=False))

            story_data_not_found = await async_get_story_description("ORI-000000")
            print(json.dumps(story_data_not_found, indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"\n执行过程中遇到错误: {e}")

    asyncio.run(main_test())
