# L05 参考证据的来源与边界

## 当前图文版使用的证据

| 文件 | 来源与用途 | 结论边界 |
|---|---|---|
| latest/workbench-task.png、workbench-eval.png | 浏览器直接截取本地原生工作台，TASK-DC0060EA39，L05 合同 | 仅复验；默认 receiving_is_idempotent 通过；未调用 Codex，未人工接受 |
| latest/web-task-record.json | 该原生任务的结构化输出 | 与下方执行器实验是两个独立记录，不拼成一次交付 |
| latest/red-evidence.png | 真实命令记录排版后截图 | 隔离服务副本显式注入重复流水；旧返回值检查绿，完整状态检查两次红 |
| latest/green-evidence.png | 真实执行与外部复验记录排版截图 | Codex 仅修入库服务，原检查不变；不是工作台原生页面 |
| latest/executor-record.json | L05-LEDGER-REPAIR 的命令、来源、检查指纹、实际输出与退出码 | 教师参考实验，不是你的学习记录；无人工接受 |
| latest/example-checks.json | 夹具、正常实现、实际临时 Git 仓库中的合法、越界、重命名检查 | 验证具体示例，不证明所有写入都受沙箱约束 |

截图说明不展示采集日期。原始记录保留真实执行时间、路径和来源，便于追溯。临时数据库相互独立；课程示例不读写业务生产数据。

2026-09-09 的讲义优化补充了 `receiving_contract_eval.py` 的流水业务字段校验，以及重放、拒绝后状态的完整前后输出。`latest/` 保留原实验和原检查指纹，未改写历史输出。当前脚本在重复流水缺陷上可能同时报告 AC-REPLAY 与 AC-NEW；复验时核对当前源码与实际结果，不要求与旧截图逐字相同。新版检查的隔离缺陷回归见 `tests/test_l05_receiving_eval.py`，它验证检查辨识力，不代表重新完成 Codex 修复或具名接受。

## 保留的历史资料

workbench/、execution/runs.json 为较早参考实验。旧 receiving_eval.py 的 --defect 改变调用方请求键，去掉开关不代表修复产品源码。新版主案例改用真实服务副本中的明确缺陷及实际执行器修复。

diagrams/ 是机制示意图，不是运行截图。原生截图没有重绘结果。所有参考绿灯都不替代你的实现、同伴复验或具名决定。
