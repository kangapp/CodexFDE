# FlowERP 接口与运行边界

本资料回答三个问题：客户端看到的状态从哪里来，系统重启后什么必须恢复，以及哪些演示结果不能被包装成“生产就绪”。

## 两个服务，两个职责

| 服务 | 默认端口 | 负责什么 | 不负责什么 |
|---|---:|---|---|
| 个人研发自动化工作台 | 8001 | 需求、Spec、任务、执行、Eval、审核、摘要和反馈 | 不重算 ERP 库存，不充当 FlowERP 员工门户 |
| FlowERP 客户项目 | 8000 | 商品、库存、订单、采购等业务操作与查询 | 不替工作台判定代码交付是否合格 |

两个服务的数据目录不得混用。页面、API 和 SQLite 必须能用同一个 `task_id` 或业务 ID 对账。

## 异步任务 API 的最小语义

提交任务后返回 `202 Accepted` 只表示请求已被接收处理，不表示完成。客户端随后按任务 ID 查询状态：

```text
queued → spec_ready → executing → evaluating → review → completed
                                   ↘ failed / rework
```

- 状态只按允许边迁移；非法跳转明确失败。
- 重复提交需要幂等边界，不能生成相互矛盾的事实。
- 失败原因和最近一次可靠状态必须可查询。
- 已完成任务在进程重启后仍可读取。
- HTTP 错误应返回机器可读的问题详情，而不是只给一段模糊文本。

## Web 面板的信息纪律

状态面板不是装饰层。它至少显示：事实来源、对应 ID、更新时间、当前状态、失败原因、可下载证据和下一动作。旧数据、未知状态和真实失败必须区分；不能用计时器制造假进度，也不能在浏览器中重算权威业务结果。

当后台状态变化而页面没有焦点移动时，状态消息应能被辅助技术感知。颜色不能成为唯一信号，错误状态必须有文本和恢复动作。

## 持久化、冷启动与回滚

一次可信冷启动使用空运行目录和版本化步骤，不复制作者电脑上的旧数据库、报告或密钥。健康检查至少区分：

- 进程是否存活；
- 数据库是否可打开和迁移；
- 关键业务查询是否一致；
- 任务与证据是否能恢复；
- 阻断级 Eval 是否通过。

容器启动成功只证明进程边界成立。它不证明备份可恢复、并发正确、容量足够或具备生产运维能力。发布摘要必须把这些未证明项列为风险。

## 安全边界

- 前端、仓库和报告中不保存密钥。
- 外部网络和高风险写操作采用最小权限与显式授权。
- CI 运行不受信任代码时不注入部署凭据。
- Artifact 是证据载体，不天然是真实性证明；要核对来源运行、提交、哈希和保留策略。
- 失败、重试、取消和超时都要留下事件，不能静默吞掉。

## 一手资料（核验：2026-09-04）

- [RFC 9110：202 Accepted](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted)：已接受与已完成的边界。
- [RFC 9457：Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)：机器可读错误合同。
- [W3C：Understanding Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)：动态状态的可访问表达。
- [OpenTelemetry：Signals](https://opentelemetry.io/docs/concepts/signals/)：traces、metrics、logs 的用途边界。
- [Google SRE：Release Engineering](https://sre.google/sre-book/release-engineering/)：可复现发布、自动化与一致门禁。
