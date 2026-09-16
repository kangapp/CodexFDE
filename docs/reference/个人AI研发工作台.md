# 个人 AI 研发工作台

> 课程定义：**工作台是主体，FlowERP 是验证场，Codex 是底座。**

个人 AI 研发工作台不是聊天窗口，也不是 FlowERP 的员工门户。它是一套把“需求、授权、执行、验证、审核、反馈”变成可追溯工程对象的本地系统。Codex 在其中负责理解仓库、提出方案、修改代码和运行命令；工作台负责给它输入、边界、质量门和停止条件；人负责业务取舍、授权与最终签收。

## 一次可信交付的最小闭环

```text
现场问题
→ 结构化 Spec
→ 受控写集与执行预算
→ Codex 产生候选 Diff
→ Eval / Harness 给出可重复证据
→ 具名人工审核
→ 摘要与反馈回流
```

任何一环都不能由一句“Agent 说成功了”替代。工具调用成功只说明动作发生；业务是否正确，要由业务不变量和独立复验判断。

## 四阶段能力增长

| 阶段 | 工作台新增什么 | 它解决什么失败 |
|---|---|---|
| V0：接管与受控执行 | 仓库接手、`AGENTS.md`、Spec、写集、最小 Eval | 模糊需求、越界修改、自报成功 |
| V1：质量证据链 | Eval、Harness、Hook、CI Artifact | 只测正常路径、本地与远端口径分裂 |
| V2：受控协作 | Repair Task、有界 Loop、Subagents、Graph、人审 | 日志直接喂模型、无限修复、并行冲突、职责混同 |
| V3：产品化与反馈 | Task API、Web 状态、摘要、反馈治理、冷启动 | 状态不可见、异步语义失真、反馈直达代码、作者依赖 |

## Codex 的能力边界

Codex 擅长在给定上下文和工具范围内探索、实现和验证，但它不天然拥有业务授权，也不能自己成为最终证据。

- `AGENTS.md` 保存长期项目规则；它影响行为，但不是操作系统权限系统。
- Hook 在生命周期节点调用脚本或 MCP 工具；项目 Hook 的来源需要审查和信任。
- Subagents 适合边界清楚、写集互不冲突的任务；并行会增加上下文、汇总和 Token 成本。
- MCP 连接仓库外的工具与数据；基本文件读写不需要为了“看起来像平台”再包一层 MCP。
- 非交互执行适合可重复任务，但必须固定工作目录、权限、超时、退出码和结果采集。

## 三种不能混淆的状态

| 状态 | 例子 | 权威来源 |
|---|---|---|
| Agent/工作台状态 | queued、executing、evaluating、review | 任务事件与工作台数据库 |
| ERP 业务状态 | order=reserved、purchase=approved | FlowERP 领域服务与业务数据库 |
| 质量判定 | pass、block、warn | Harness 报告与退出码 |

一个任务 `completed` 不等于采购已批准；页面显示绿色不等于库存正确；Hook 运行过不等于 CI 已复验。

## 可选完整 Harness 的边界

仓库中的 `harness_web/` 用来对照 Session/Profile/Plugin、thread、event stream、approval 和 interrupt 等平台概念，属于可选挑战。它不是 L01～L16 的必做工作台，也不得声称已经等价于 DeepSeek Harness、Codex Harness 或接入官方 app-server。基础通过仍以 `workbench/`、`:8001`、统一 Eval 和具名人工审核为准。

## 证据最小集

学生每次提交至少保留：

- 原始需求和已签署 Spec；
- 执行前稳定红灯及退出码；
- 允许写集和实际 Diff；
- 同一用例的执行后绿灯；
- 失败后业务状态不变的证明；
- 具名审核结论；
- 剩余风险和可复现命令。

## 一手资料（核验：2026-09-04）

- [OpenAI：Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：规则的发现顺序与作用域。
- [OpenAI：Hooks](https://learn.chatgpt.com/docs/hooks)：生命周期事件、信任和失败行为。
- [OpenAI：Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)：委托、隔离和汇总边界。
- [OpenAI：Model Context Protocol](https://learn.chatgpt.com/docs/extend/mcp)：外部工具连接边界。
- [OpenAI：Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)：评价样本、判定与持续评估原则。
