<p align="center">
  <img src="docs/assets/medalloop-cover.webp" alt="MedalLoop：机器学习竞赛 Agent 迭代框架" width="960">
</p>

# MedalLoop

**面向机器学习竞赛提分的 Agent 迭代框架。**

[English](README.md) · [竞赛工作流](docs/competition-workflow.md) ·
[配置说明](docs/configuration.md) · [贡献指南](CONTRIBUTING.md)

MedalLoop 用来让代码 Agent 持续推进一场机器学习竞赛：

<img src="docs/assets/workflow.png" alt="竞赛迭代流程：理解赛题、实验、评估、融合提交，再更新记忆并选择下一项假设。" width="960">

它解决的不是“如何让 Agent 一次写出一个模型”，而是如何让 Agent
在数天或数周的竞赛过程中，记住当前最佳方案，控制变量地做实验，
保留失败经验，管理 CV 与榜单反馈，并在没有收益时及时换方向。

> MedalLoop 仅用于遵守比赛规则的算法研究。它不会访问隐藏标签、
> 绕过平台规则、伪造榜单成绩，也无法保证获奖或提分。

## 快速开始

需要 Python 3.9 或更新版本：

```bash
git clone https://github.com/Chengyuann/medalloop.git
cd medalloop
python -m venv .venv
source .venv/bin/activate
python -m pip install .

medalloop init my-competition --competition
cd my-competition
```

Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 激活环境。
当前从仓库安装，尚未发布到 PyPI。

初始化后会生成：

```text
my-competition/
├── AGENTS.md                 # 竞赛 Agent 完整操作流程
├── COMPETITION.md            # 赛题、规则、指标、数据和预算
├── memory/
│   ├── STATE.md              # 当前最佳方案、活跃轮次、下一步
│   ├── HYPOTHESES.md         # 提分假设池
│   └── RESULTS.md            # CV 结论和官方提交记录
└── rounds/
    └── 001/
        ├── README.md         # 首轮待完成事项
        └── loop.json         # 基线实验计划
```

把 `AGENTS.md` 交给 Codex、Claude Code、Cursor 或其他代码 Agent。
先补全 `COMPETITION.md`，让 Agent 阅读规则和数据、选择合理 CV、
实现 `rounds/001/train.py`，再审查并执行：

```bash
medalloop plan --root rounds/001
medalloop run --root rounds/001 --steps 1 --execute
medalloop report --root rounds/001
medalloop verify --root rounds/001
```

`--execute` 表示你已审查本地命令。训练代码会继承当前用户权限，
MedalLoop 不是安全沙箱。

## 一轮竞赛迭代包含什么

### 1. 先把本地评测做可信

Agent 先确认官方指标、方向、提交格式、数据结构和比赛规则，
再根据分组、时间、类别分布等信息选择 Stratified、Group、Time
或其他合理切分。基线必须能够输出固定 folds、OOF、测试集预测、
配置、指标和合法 submission。

### 2. 从证据中选下一项实验

Agent 会结合公开方案调研、错误切片、折间波动、历史失败和算力预算，
维护一个提分假设池。每个任务只保留一个主要变量，例如：

- 数据清理和特征工程；
- 表征、模型家族、损失函数；
- 采样、增强、训练策略、参数调整；
- 推理策略和互补模型融合。

不是所有比赛都需要所有方向。优先做有证据、有信息增益的实验。

### 3. 实际执行并判断是否保留

每个任务声明假设、训练命令、指标文件和必要产物：

```json
{
  "id": "text_features_v2",
  "hypothesis": "字符特征改善稀有类别样本。",
  "command": ["{python}", "train.py", "--config", "text_features_v2.json"],
  "metrics": "metrics.json",
  "artifacts": ["oof.csv", "submission.csv", "config.json"]
}
```

训练脚本把结果写入 `MEDALLOOP_RUN_DIR`。MedalLoop 检查指标名、
评估协议、文件是否齐全，保存日志和哈希，并按 maximize/minimize
方向与当前结果比较。程序正常结束但没有提分，也会被明确标记为拒绝。

### 4. 失败也要产生信息

失败需要区分：

- 数据或实现错误；
- 指标或切分错误；
- 超时、显存、内存等资源问题；
- 算法假设本身没有收益。

CV 提升需要查看各折和关键错误切片；CV 与榜单方向不一致时，
优先排查切分、分布偏移和 public LB 过拟合，而不是直接相信较高分数。

### 5. 用 OOF 做互补性融合

融合前应保证 OOF 行、fold 和评估协议一致。不同模型名字不代表真的互补。

```bash
medalloop blend predictions/a.csv predictions/b.csv \
  --id-column row_id --weight 0.25 --output submissions/blend.csv
```

支持 mean 与 rank blending。Rank 结果不一定是校准概率，是否适合需要结合指标判断。

### 6. 提交前检查并记录榜单反馈

```bash
medalloop check-submission submissions/blend.csv \
  --id-column row_id --sample data/sample_submission.csv
```

工具会检查表头、行宽、ID、顺序、空值、非有限数值和常数预测。
它不会自动上传。由 Agent 或操作者显式提交后，将官方分数、文件哈希、
来源实验和回执记录到 `memory/RESULTS.md`。

### 7. 开启下一轮

当实验计划或评估协议发生变化时，新建 `rounds/002`。上一轮最佳方案
需要作为新一轮的第一项重新评估，不能在不同协议之间直接比较。
连续没有改善时，应该分析错误或调研新的方向，而不是静默扩大预算。

## 两层结构

```text
竞赛 Agent 层
  规则 / 调研 / 假设 / 编码 / 错误分析 / 融合 / 下一轮决策
                              ↓
确定性实验执行层
  训练命令 / 指标校验 / 实验记录 / 恢复重试 / 停止条件 / 提交检查
```

项目不绑定任何大模型供应商。Agent 负责竞赛研究和写代码，
底层执行器使用 Python 标准库，运行时零第三方依赖。

## 能力范围

竞赛研究、模型实现、记忆更新和榜单复盘由外部代码 Agent 按指令完成；
CLI 负责一轮内的执行、结果检查和记录。提交上传和资源支出需要明确授权。

请遵守比赛的数据与模型使用规则。验证切分、泄漏审查和算法质量仍需
结合具体赛题判断，框架不保证奖牌或线上提分。

## 兼容与许可

v0.2 保留 `evidence-loop` 命令作为兼容别名，新项目使用 `medalloop`。
MIT License，维护者 Chengyuan Ma。
