# L08 图解与实验来源

`diagrams/` 是教学流程与状态示意。`latest/atomic-*.json` 为正式销售服务的真实临时库实验，包含四表前后状态；缺货与第二次写入故障分别检查写入前拒绝和写入后回滚。

`latest/signal-*.json` 使用真实 Harness 配合教学断言，只验证本地信号传播；`envelope-*.json` 使用明确标注的 SIMULATED 身份，观察信封函数边界。

`A-false-green.json`、`B-true-red.json`、`C-true-green.json` 为真实隔离产品、真实 Harness 与真实外层 Python 进程对照。A、B 产品内容相同，三次检查内容相同；教师在 C 恢复原事务。对应 HTML/PNG 是运行记录排版截图，不是 GitHub 页面。`partial-write-state.json` 从 A 的原始失败断言提取完整四表状态；`injected-atomic-defect.diff` 保存故意提前提交的缺陷。

没有远程运行、真实客户事故、学生实现或具名人审记录。机器运行时间保留在报告，教学图注不展示日期。远程验证须按实践手册另行完成。
