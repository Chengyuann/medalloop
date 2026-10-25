<p align="center">
  <img src="docs/assets/cover.webp" alt="Evidence Loop：让实验结论有据可查。" width="900">
</p>

# Evidence Loop

**为代码 Agent 和研究者提供可执行、可核验、可恢复的本地实验闭环。**

[English](README.md) · [架构](docs/architecture.md) ·
[配置说明](docs/configuration.md) · [贡献指南](CONTRIBUTING.md)

提出假设不等于得到结果，程序正常结束也不等于实验有效。
Evidence Loop 把实验流程变成一组明确动作：

```text
提出假设 → 执行命令 → 校验指标与产物 → 留存证据 → 保留或拒绝 → 继续或停止
```

它不是一个内置大模型的自主科研系统，而是可以由人或任意代码 Agent
调用的确定性执行工具。默认不联网，不需要 API Key，不依赖 GPU，
运行时没有第三方 Python 依赖。

> 当前为早期版本 v0.1.0。演示使用合成数据，用于验证工作流，
> 不代表真实任务上的效果提升或竞赛成绩。

## 快速开始

需要 Python 3.9 或更新版本。目前从仓库安装，尚未发布到 PyPI。

```bash
git clone https://github.com/Chengyuann/evidence-loop.git
cd evidence-loop
python -m venv .venv
source .venv/bin/activate
python -m pip install .

evidence-loop init workspaces/demo
evidence-loop plan --root workspaces/demo
evidence-loop run --root workspaces/demo --execute
evidence-loop report --root workspaces/demo
evidence-loop verify --root workspaces/demo
```

Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。
也可以用 `python -m evidence_loop` 调用相同命令。

**先看 plan，再决定是否执行。** `--execute` 表示信任这些本地命令；
程序不是沙箱，子进程具有当前用户的权限和环境变量。

## 演示会发生什么

<img src="docs/assets/demo.png" alt="实际离线演示：建立基线、保留线性模型、拒绝偏移与重复实验，然后停止。" width="900">

1. 用训练集均值建立基线。
2. 拟合线性模型，在同一合成留出集上评估。
3. 测试固定截距偏移。
4. 重复固定随机种子的线性实验。
5. 连续两次没有改善后停止，剩余任务不会执行。

再次执行同一 workspace，不会重复已完成的任务。
退出或重启不会清空实验记录与停止状态。

## 主要改进

| 问题 | 实现 |
| --- | --- |
| Loop 只输出建议 | 实际运行 argv 命令并管理超时。 |
| 失败记录不完整 | SQLite 保存每次尝试、状态、原因和结果。 |
| 重启后重复运行 | 按任务与尝试编号恢复，失败需要显式 retry。 |
| 分数比较不严谨 | 固定指标名、方向和评估协议，仅比较校验通过的结果。 |
| 程序结束就算成功 | 区分运行成功、结果保留、结果拒绝。 |
| 配置形同虚设 | 实际执行次数、总耗时、连续失败与无改善停止条件。 |
| 文件存在但无法追溯 | 保存文件大小、SHA-256、命令与 Python 版本。 |
| CSV 错位或静默补值 | 严格校验表头、行宽、ID 集合、顺序和数值。 |
| 并列排名处理错误 | Rank blending 使用并列平均排名。 |

## 接入自己的实验

在第一次执行前修改 workspace 下的 `loop.json` 与实验脚本。
每个任务写清假设、命令、指标文件和产物列表。

脚本从环境变量 `EVIDENCE_LOOP_RUN_DIR` 获取本次输出目录，
并写入以下格式的 `metrics.json`：

```json
{
  "metric": {"name": "mse", "value": 0.25},
  "evaluation_id": "my-fixed-dataset-split-v1"
}
```

指标名与 `evaluation_id` 必须与配置一致，分数必须是有限数值。
原始日志、指标、预测文件及哈希记录都保留在本地。
配置开始运行后被锁定，新一轮方案使用新的 workspace。

常用命令：

```bash
evidence-loop run --root workspaces/demo --steps 1 --execute
evidence-loop status --root workspaces/demo
evidence-loop check-submission submission.csv --id-column row_id --sample sample.csv
evidence-loop blend a.csv b.csv --id-column row_id --output blend.csv
```

对于实际失败的任务，使用 `retry TASK_ID --root WORKSPACE --execute`。
重试会新增一次尝试，旧失败不会被删除，也不会重置总预算。

## 边界

- 不自动生成研究方案，不内置模型服务，也不自动提交竞赛结果。
- 文件哈希只能检测相对本地记录的变化，不是不可篡改的证明。
- 指标格式正确不代表指标实现正确；泄漏、切分、显著性与数据权限需要单独审查。
- `evaluation_id` 是协议约定，不会自动检测底层数据是否被更换。
- 不提供网络隔离、GPU 限额、Token 计费或分布式调度。
- 不能捕获的进程终止可能遗留子进程，恢复前应检查运行状态。
- 本地 workspace 可能含隐私，不应直接作为公开资料上传。

## 开发与贡献

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=evidence_loop
ruff check .
ruff format --check .
python -m build
```

欢迎最小可复现问题、失败案例和小范围改进。请只提交合成测试数据，
不要附带真实数据、内部链接、凭证、个人路径或未脱敏日志。

## 许可

MIT。维护者：Chengyuan Ma。封面使用 GPT Image 2 生成；
演示图来自实际合成实验记录。详情见 [素材说明](docs/assets/README.md)。
