---
date: 2026-04-08
sequence: 002
type: plan
title: "Polymarket V3 Harness 运行模型"
status: active
origin: docs/plans/2026-04-07-001-feat-polymarket-phase1-validation-bot-plan.md
---

# Polymarket V3 Harness 运行模型

## 这份文档是干什么的

这份文档用来定义：AI 应该如何参与 Polymarket V3 项目。

目标不是让 AI “自由发挥去做一个机器人”，而是把 AI 放进一个受控的工程框架里，在提高推进效率的同时，不破坏以下底线：

- 风控真实有效
- 技术结构清楚
- 验证证据完整
- 阶段升级有门槛
- 操作结果可被信任

对于这个项目，Harness 不是附属品，而是和策略代码同等重要的基础设施。

## 项目级 Harness 原则

AI 可以作为以下工作的放大器：

- 方案整理
- 实现推进
- 测试设计与验证
- replay 分析
- paper 结果复盘
- 运行总结

但在一期阶段，不允许把 AI 当成一个不受约束的 live 交易大脑。

一期 live 相关行为必须保持：

- 规则明确
- 可测试
- 可回放
- 可审计
- 可解释

LLM 可以服务于交易系统外围，但不应进入一期 live 决策关键链路。

## Harness 七层结构

### 1. 目标与验收契约

每次给 AI 一个任务，都必须先写清楚：

- 目标结果是什么
- 范围边界是什么
- 允许动哪些模块或文件
- 必须做哪些验证
- 明确禁止哪些动作
- 最终输出格式是什么

本仓库默认的任务完成格式：

1. 改了什么
2. 验证了什么
3. 哪些部分还没验证
4. 当前主要风险是什么
5. 下一步最值得做什么

### 2. 上下文管理

AI 不能靠模糊记忆工作。每次任务都应有一个最小必要上下文包。

本项目默认上下文优先级：

1. `docs/brainstorms/2026-04-07-polymarket-auto-trading-income-system-requirements.md`
2. `docs/plans/2026-04-07-001-feat-polymarket-phase1-validation-bot-plan.md`
3. 本文档
4. 当前任务直接相关的实现文件
5. 当前任务直接相关的测试文件
6. 当前任务直接相关的 replay / paper 工件

上下文规则：

- 能小范围完成，就不要整仓库塞给 AI
- 改某个模块时，要同时读取该模块对应测试
- 改风险规则时，要同时读取阶段门槛和 promotion 规则
- 改操作台字段时，要同时读取相关 fixture、快照或说明文档

### 3. 工具系统

AI 可以使用工具，但必须分层授权。

允许的工具类别：

- 读文件
- 改文件
- 跑 lint
- 跑单元测试和集成测试
- 跑 replay / paper 分析脚本
- 本地 dashboard 验证
- 日志检查

受限的工具类别：

- 真实下单
- 钱包和密钥处理
- 生产环境修改
- 不可逆链上动作

规则：

- `paper` 模式可以在明确范围下由 AI 辅助运行
- `live_small` 不允许由 AI 自行启动、自行改配置、自行升级阶段
- AI 可以读取 live 产物并给出建议，但不能自行授权进入真实资金验证

### 4. 执行编排

本项目不应该靠临时 prompt 推进，而应该用固定工作链路。

默认执行流程：

1. 定义任务
2. 读取最小必要上下文
3. 理解当前实现与限制
4. 做一次有边界的修改或分析
5. 做贴近改动的验证
6. 总结证据和剩余风险
7. 明确停止点或升级条件

对较大的任务，概念上可以拆成四种角色：

- `架构者`：把业务目标整理成可执行边界
- `实现者`：只负责完成当前小块内容
- `验证者`：负责测试、回放、回归检查
- `运行分析者`：负责总结系统表现和是否可晋级

这四个角色可以由同一个 AI 会话承担，但职责必须分清。

### 5. 状态与记忆

这个项目的长期记忆不能只存在聊天里，必须落成可追踪工件。

必须沉淀的记忆类型：

- 需求文档
- 活跃计划
- 配置 profile
- replay 工件
- paper 工件
- promotion 决策
- 风险事件记录
- 运行总结

建议存放位置：

- `docs/brainstorms/`：问题定义与需求
- `docs/plans/`：计划、Harness 规则、阶段门槛
- `artifacts/replay/`：replay 结果
- `artifacts/paper/`：paper 结果
- `artifacts/live_small/`：经批准的真实小额验证工件
- `artifacts/incidents/`：收手事件、异常、漂移、调查记录

记忆规则：

- promotion 决策必须引用工件，不能靠感觉
- 一次运行总结必须能从文件和日志重建出来
- 一个关键判断如果没有落到文件或日志里，就不能算受控

### 6. 评估与观测

Harness 必须持续回答这些问题：

- 系统现在健康吗
- 策略行为是否符合设计
- 某条规则是否真的触发了
- 当前是否有资格进入下一阶段

各阶段最低证据要求：

- `architecture`
  - requirements
  - implementation plan
  - harness 规则
  - 风险边界定义
- `local_validation`
  - 单元测试
  - 集成测试
  - 基于 fixture 的状态机验证
- `paper_canary`
  - 每日 session summary
  - probe outcome log
  - stop reason log
  - weekly pnl summary
- `small_live_validation`
  - 包含全部 paper 工件
  - 余额与持仓对账证据
  - 重启恢复证据
  - 限额触发或保护触发证据

面向操作者至少应可见：

- 当前运行模式
- 当前 session 状态
- 当前持仓
- 已实现 / 未实现 pnl
- 最近一次 stop 原因
- 最近一次 reconcile 结果
- kill switch 是否生效

### 7. 约束与恢复

对这个项目来说，这是最关键的一层。

硬约束：

- 没有人工明确授权，不允许进入真实资金验证
- 不允许静默绕过 kill switch
- 不允许策略层直接耦合交易所细节
- 每次新决策前必须先完成 reconcile
- 没有证据工件，不允许 promotion
- 配置里写了保护但没接入执行链路，不算保护已完成

恢复要求：

- 重启后必须先 reconcile，再允许新动作
- 外部 API 失败时必须安全降级
- reference probability stale 时禁止新增风险
- 单个 session 内连续两次 probe 未确认时必须收手
- kill switch 必须进入 execution 检查链，而不是只显示在 UI 上

## 这个项目当前适合的 Harness 形状

Polymarket V3 建议按六条工作轨道推进。

### 轨道 A：产品与策略定义

目标：

- 收窄一期市场类型
- 定义 edge 标准
- 冻结一期阶段语义

产物：

- requirements
- strategy notes
- promotion criteria

### 轨道 B：核心工程

目标：

- 建立 domain、storage、strategy、execution、web 的清晰边界

产物：

- 代码
- 测试
- schema
- run scripts

### 轨道 C：风控与治理

目标：

- 确保所有 live 保护都是真正生效，而不是写在文档里

产物：

- live guard config
- kill switch 链路
- session stop 规则
- promotion gate 检查

### 轨道 D：证据流水线

目标：

- 让每个验证阶段都能沉淀可复用证据

产物：

- replay 工件
- paper 总结
- stop 报告
- weekly / monthly snapshot

### 轨道 E：操作台

目标：

- 用一页结果面板真实展示系统状态

产物：

- 单页 dashboard
- mode / status summary
- 最近一次 stop 与 reconcile 结果

### 轨道 F：AI 协作规则

目标：

- 规定 AI 如何在上述轨道中参与，何时停下，输出什么

产物：

- 本文档
- 后续任务模板
- 安全执行清单

## 适合本仓库的 AI 任务模板

以后你给 AI 分配重要任务时，建议统一用这个模板：

```text
本次目标：
[这次完成后，什么结果必须成立]

范围边界：
[这次只处理哪些模块、文件或流程]

必读上下文：
[这次必须先看哪些文档、代码、测试、工件]

允许动作：
[允许分析、修改、测试、运行哪些本地内容]

禁止动作：
[禁止进入 live、禁止处理密钥、禁止跳过风控、禁止改生产]

验收标准：
[哪些检查必须通过，才算完成]

输出要求：
1. 改了什么
2. 验证了什么
3. 哪些还没验证
4. 当前主要风险
5. 下一步建议
```

## 阶段门槛

这个项目必须明确使用阶段语言。

### 阶段：`architecture`

含义：

- 有 requirements
- 有 phase-1 计划
- 有 harness 与风险边界
- 还没有资格宣称 production-ready

进入条件：

- 问题定义和一期计划已存在

退出条件：

- foundation 层的实现计划已经清晰到可以开工

### 阶段：`local_validation`

含义：

- 已有代码
- 关键路径已有测试
- 不涉及真实资金

退出条件：

- trading loop、reconcile、risk、dashboard 都能在 fixture 条件下闭环验证

### 阶段：`paper_canary`

含义：

- 使用与未来相同的主交易链路
- 不进行真实下单
- 开始稳定产出验证工件

退出条件：

- paper 结果稳定到足以支持小额真实验证评估

### 阶段：`small_live_validation`

含义：

- 使用真实资金，但严格限额
- 所有硬保护已接入真实执行路径
- 有明确人工授权

退出条件：

- 已积累 2 到 3 周支持 promotion review 的证据

### 明确禁止的过度表述

在证据不足前，不应把系统表述为：

- production-ready
- live-ready
- 可正式使用

除非当前阶段和证据链真的支撑这个说法。

## 这个项目里，AI 最应该先做什么

推荐顺序：

1. 先冻结 foundation contract
2. 再搭仓库基础骨架和工具基线
3. 先做 domain 和 storage
4. 再做 market discovery 与 selector
5. 再做 risk、execution、reconcile
6. 然后做 dashboard
7. 最后补 artifact generation 和 promotion checks

第一波工作不应该从 UI 花样和策略扩展开始。

## 当前最合适的下一步

1. 把当前阶段明确叫做 `architecture`
2. 把现有 phase-1 plan 作为实现主骨架
3. 把本文档作为所有 AI 协作的规则基线
4. 真正开工时，优先从 foundation 和风险关键路径开始
5. 在没有 replay、paper、guard evidence 前，不允许 AI 推动 live 行为升级
