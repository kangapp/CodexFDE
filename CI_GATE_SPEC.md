# L08 个人CI_GATE_SPEC：原子预占与可信复验

## 来源
刘付康请求逐步完成L08，已确认首次判断；工作台事项INIT-3DBC15F863，来源L07已接受任务TASK-695D312A94。
控制工作台：/Users/liufukang/Workplace/CodexFDE/.runtime/course-worktrees/TASK-L01-20260916-233343-30671；沿用运行目录：/Users/liufukang/Workplace/CodexFDE/.runtime/course-worktrees/TASK-L01-20260916-233343-30671/.runtime/l04-learning。
本次隔离候选：/Users/liufukang/Workplace/CodexFDE/.runtime/course-worktrees/TASK-L01-20260916-233343-30671/.runtime/l04-learning/course-worktrees/TASK-PREP-L08-PERSONAL-521b1b8fe004；候选自己的解释器：/Users/liufukang/Workplace/CodexFDE/.runtime/course-worktrees/TASK-L01-20260916-233343-30671/.runtime/l04-learning/course-worktrees/TASK-PREP-L08-PERSONAL-521b1b8fe004/.venv/bin/python。
使用显式两仓源码快照，不是已发布课程标签。正式产品第2步参考实验通过；prepare在入门门面与信封身份校验剥离能力，Codex另在正式SalesService加入过早按行commit以构造中途失败反例，来源与Diff见step4-teaching-injection.json。全部缺陷均为教学设置，不是客户事故。

## 目标
使用正式SalesService.reserve交付整单原子预占；保留旧接口库存不足必须拒绝的规则。
固定成功、第二行缺货、第二次写入失败的四表要求及个人检查。通过同一候选、同一检查的A假绿、B可信红、C可信绿分别判断流程修复和业务修复。

## 非目标
不改控制仓库或独立客户原工作区，不在控制仓库恢复flowerp；不删除、降级或弱化已冻结检查；不复制另一套业务规则到工作流。
不将教学结果或SIMULATED身份当远程运行，不伪造同伴意见和人审，不自动合并主分支。
本阶段只准备候选、检查与教学反例，不运行远程A/B/C，不提前修复业务或失败传播。

## 约束
正式入口SalesService.reserve；四表stock_balance、stock_reservations、sales_document_lines、sales_documents完整比较。
检查准备仅eval/l08_atomic_checks.py、eval/erp_cases.py、eval/cases.py、eval/harness.py和本Spec。正式销售教学注入仅flowerp/sales.py，保留准备工具的旧缺陷。
A到B保持flowerp全部业务、业务检查、数据和环境不变；B仅允许必要的.github/workflows/eval.yml及workbench/ci_evidence.py失败传播、身份验证与本次报告归档改动，不修改业务或检查。
B到C保持检查、等级、入口、数据和B工作流不变；C业务写集限flowerp/sales.py和flowerp/service.py，分别恢复正式预占事务及准备工具剥离的旧接口缺货拒绝；不增加业务功能。
个人检查须归为PROJECT_CASES且显式执行；默认完整blocking只检查工作台。保留完整默认工作台报告和显式完整业务报告，不用其中一份替代另一份。
远程前将组合候选按两仓来源拆回各自候选分支，显式运行同一检查验证一致；A/B产品使用同一40位SHA，C才换业务修复SHA。远程工作流、两仓实际checkout、Run/attempt、内外退出码、报告哈希与原始产物分别留证。
每次新建输出目录，缺报告、空用例、错误候选、汇总与分项或退出码矛盾均不能交接；信封生成不能替代报告语义核验。远程条件未具备则标待验证。
本地检查全部使用临时SQLite数据库，不接触运行数据库；本轮不证明并发或生产状态。

## 验收用例
l08_personal_atomic_success：库存5/5，预占2/3，预占记录两条、明细已预占2/3、可用3/2、订单reserved、在库仍5/5。
l08_personal_atomic_shortage：库存5/2，申请2/3；必须InsufficientStock，四表原样、预占0/0、可用5/2、订单confirmed。
l08_personal_atomic_write_error：库存5/5，临时SQLite触发器使第二条预占记录插入失败；必须目标IntegrityError，四表原样、预占0/0、可用5/5、订单confirmed。
原有19项产品检查全部保留，加个人3项共22项；重点保留stock_never_negative、sales_credit_and_atomic_reservation和order_total_matches_lines。
A：真实报告block且内部非零、外层假绿；B：仅修流程后业务仍block且Job失败；C：仅修业务后同一业务22项及默认工作台12项均pass、对应命令退出0。实际远程状态以平台来源为准。

## 完成定义
第4步：候选来源、准备阶段Diff、模块与解释器位置可回查；三个个人检查各单独运行并保存原始报告；完整默认和显式业务集合实际运行，已知教学缺陷稳定被发现；检查与业务对照条件冻结。
最终完成另需双仓拆分一致性、真实远程A/B/C及下载核对、独立复验意见、本人具名审核；远程绿灯不自动接受。后续阶段的实际修复必须另按已冻结范围委托，不把本阶段准备等同于业务修复完成。
