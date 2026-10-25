# Launch Copy

Draft copy for maintainer-led sharing. These are not automated posts or
performance claims.

## Short Introduction

I built Evidence Loop because an agent saying "the experiment worked" is not
enough.

It is a small, local Python CLI that runs reviewed experiment plans, checks
metrics against a fixed evaluation protocol, saves artifact hashes, preserves
failed attempts, and stops when its budget or patience runs out.

No API key, cloud service, or runtime dependencies. The included offline example
runs on synthetic data and demonstrates keep/reject decisions, stopping, and
restart-safe behavior.

Repository: https://github.com/Chengyuann/evidence-loop

I would appreciate feedback on the output contract and real workflows where
experiment tracking or recovery currently breaks.

## 中文介绍

我开源了 Evidence Loop，一个给代码 Agent 和研究者使用的轻量实验闭环工具。

它解决的问题很具体：Agent 说“实验成功了”，不应该只剩一句话。
每次尝试都要有运行记录、指标、产物和可复核的文件哈希；
失败要保留，重试要明确，没有改善要停下来。

纯本地 Python CLI，运行时零第三方依赖，无需 API Key。
仓库提供可以直接跑通的合成数据示例，也支持接入已有实验脚本。

这不是自主夺冠系统，也不是安全沙箱。欢迎反馈实验恢复、指标校验
和 Agent 接入过程中真正遇到的问题。

仓库：https://github.com/Chengyuann/evidence-loop
