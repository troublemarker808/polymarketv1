---
date: 2026-04-07
sequence: 001
type: feat
title: "feat: Build phase-1 Polymarket validation bot"
status: active
origin: docs/brainstorms/2026-04-07-polymarket-auto-trading-income-system-requirements.md
---

# feat: Build phase-1 Polymarket validation bot

## Problem Frame

> Long-term alignment: phase-1 is not the final product shape. It is the foundation layer for an account-level stable money-printing machine. Internally the system may later grow multiple earning modes, but externally it should still be judged as one machine by the total account result.

第一阶段不是做一个完整交易平台，而是做出一套可控的、可验证的、可逐步放大的自动交易基础版本。

这个版本的目标不是覆盖很多市场，也不是追求复杂策略，而是先在一个很窄的 Polymarket 场景里证明四件事：

1. 系统能持续挑出值得盯的市场
2. 系统会用小仓试探验证机会真假
3. 系统会在环境不对时主动收手
4. 系统可以在小额真钱条件下连续 2 到 3 周整体赚钱

这份计划只解决第一阶段技术落地。后续多策略、多场景扩张、产品化控制台、资金放大，不在本计划范围内。

当前已确认的第一阶段策略方向是：

- 市场类型优先切入 `体育赛果类`
- 只做 `几天内会出结果` 的市场
- 优先寻找 `被低估的更强一方`
- 第一版先以 `市场价格本身` 作为主要识别依据
- 只做 `明显但少见` 的价格优势
- 小仓试探定位为“花很小成本买确认”
- 试探应在 `当日内` 看出真假，未确认则退出
- `live_small` 采用严格限额型风格

当前建议的第一阶段默认参数风格是：

- 中等关注度默认按 `流动性中间区间` 定义，而不是按联赛名气定义
- 优势阈值采用 `中严` 风格，不极端稀有，但明显高于普通噪音
- `probe` 采用 `账户比例 + 固定金额` 双保险，且偏保守
- 日内亏损上限采用 `账户比例 + 固定金额` 双保险，风格为普通保守

## Origin Requirements Trace

来源文档：[2026-04-07-polymarket-auto-trading-income-system-requirements.md](C:/Users/Admin/Documents/New%20project%202/docs/brainstorms/2026-04-07-polymarket-auto-trading-income-system-requirements.md)

本计划重点落实以下需求：

- R8-R11：小额真钱试错、周月结果口径、不要用包装掩盖收益问题
- R15-R18：先盯几天内出结果的明确事件市场，先做市场筛选
- R19-R25：小仓试探、短窗口确认、两步加仓、两次未确认则收手
- R26-R30：首页单页结果板，不做复杂多页界面

## Context & Research

### What already exists

- 仓库当前基本为空，没有现成交易框架、风控模块、事件日志、执行层或 dashboard 可以复用。
- 这意味着第一版可以按最小正确结构设计，不需要兼容历史包袱。
- 同时也意味着所有高风险底座都必须在第一版明确建立，不能靠“以后补”。

### External references

- Polymarket 官方 API 参考：[docs.polymarket.com/api-reference](https://docs.polymarket.com/api-reference)
- Polymarket 官方 Gamma Markets API 概览：[docs.polymarket.com/developers/gamma-markets-api/overview](https://docs.polymarket.com/developers/gamma-markets-api/overview)
- Polymarket 官方 Python CLOB 客户端：[github.com/Polymarket/py-clob-client](https://github.com/Polymarket/py-clob-client)

这些资料说明第一阶段至少需要两类接入：

- `Gamma API`：做市场发现、事件元数据和结果窗口筛选
- `CLOB API`：做盘口、下单、订单状态、成交与账户相关查询

### Planning implications from research

- 第一阶段不是高频交易，决策窗口以“几天内出结果”为主，不需要为了毫秒级延迟引入复杂语言和基础设施。
- Polymarket 已有官方 Python 客户端，第一阶段应优先减少语言数量和集成复杂度。
- 由于真实资金会参与，系统必须把“交易所返回状态 + 本地账本对账”作为硬要求，而不是把 UI 账面数当真相。

## Scope Boundary

> Alignment note: phase-1 intentionally stays narrow, but its architecture should preserve the future possibility that the system becomes one externally simple machine with multiple internal earning modes.

### In scope

- 单一语言、单仓库实现第一阶段最小可运行系统
- 单页结果板
- Polymarket 市场发现、筛选、试探、加仓、收手的完整闭环
- paper mode 和 small-live mode 共用同一策略主链路
- 本地持久化、重启恢复、订单/成交/持仓/PnL 对账
- 基础风险限制、人工停机、环境收手机制
- 体育赛果类单策略闭环验证

### NOT in scope

- 多策略框架
- 多页 dashboard
- LLM 驱动的实时交易决策
- 多交易场所抽象层
- 自动扩大本金
- 复杂回测平台
- 对外产品能力，如账号体系、多人协作、云部署、多租户
- 仓库内同时维护两套主语言实现

## Key Technical Decisions

1. **第一阶段主语言选 Python 3.12**
   理由：官方 `py-clob-client` 可直接用于 CLOB 接入，Python 对策略迭代、数据处理、测试夹具和小团队快速验证更友好；第一阶段不是高频系统，不值得为了“也许以后更快”引入双语言复杂度。

2. **第一阶段尽量单语言到底**
   后端交易主循环、风险引擎、持久化、单页结果板都用 Python 完成。这样第一阶段不会把精力浪费在跨语言 DTO、双构建链、双测试栈上。

3. **前台只做单页结果板，采用 FastAPI + server-rendered HTML**
   用户明确拒绝花哨多页界面。第一阶段只需要一个稳定的本地单页，展示结果、状态和最少必要操作。没有必要先上 React/Next.js。

4. **系统必须同时支持 `paper` 和 `live_small` 两种执行模式**
   同一个策略循环、同一个状态机、同一套风险规则，先在 paper 里跑通，再切 small-live。不能做两套逻辑，不然 paper/live 会失真。

5. **交易所状态 + 本地账本双层真相模型**
   - 交易所是订单、成交、余额、在外仓位的外部真相源
   - 本地账本是策略决策、试探阶段、收手状态、PnL 展示和重启恢复的内部真相源
   - 每次做新决策前必须先完成对账，防止“以为轻仓，实际重仓”

6. **第一阶段策略循环采用确定性规则，不把 LLM 放进执行关键路径**
   现在最重要的是做出可测试、可复盘、可收手的真钱验证系统。LLM 可用于后续研究工具，但不进入第一阶段 live 决策闭环。

7. **风险控制是真实执行链路的一部分，不是文档声明**
   最低要求：
   - 单市场最大风险敞口
   - 单日最大亏损
   - 每次试探最大资金占用
   - 手动 kill switch
   - 连续 2 次试探未确认则当天收手
   - 重启后先对账，再允许恢复交易

8. **先建立仓库工程底座，再写业务模块**
   第一版虽然小，但它是正式工程起点。必须先统一依赖管理、静态检查、测试、pre-commit 和 CI，不允许每个模块各长各的。

9. **模块依赖必须单向，禁止跨层偷穿**
   目标依赖方向：
   - `domain` 不依赖任何 IO 层
   - `strategy` / `risk` 只依赖 `domain`
   - `execution` 可依赖 `domain`、`risk`、`storage`
   - `integrations` 只负责外部协议适配，不承载策略判断
   - `web` 只读聚合结果，不直接碰交易所

10. **外部 API 模型必须通过反腐层进入内部模型**
    Polymarket 的原始字段只能停留在 `integrations/polymarket/`。一旦进入策略、风控、执行判断，必须转换成内部稳定对象，避免外部接口变更污染核心逻辑。

11. **数据库只允许单写者路径**
    交易循环是唯一写入业务状态的入口。Web 层、脚本层和调试工具都不允许直接改业务表，只能通过受控服务接口请求状态变化。

12. **账本可重放、read model 可重建是硬契约**
    首页数据不是一组缓存数字，而是账本投影。任何 schema 演进都必须保证历史账本可迁移、可回放、可重新生成 read model。

13. **第一阶段策略只实现一个窄闭环，不抽象成多策略平台**
    第一版默认只服务“体育赛果类、被低估的更强一方、价格主导识别、当日内确认”的单一闭环。先做真，再谈泛化。

14. **第一阶段默认参数采用“小比例 + 小绝对金额 + 相对阈值”组合**
    这样既能适配不同验证本金规模，又能避免在小账户或大账户上出现失真。

15. **第一版必须先有一个可测试的胜率估计器，再谈 edge**
    “至少 4 个百分点优势”只有在内部估计胜率存在时才有意义。第一阶段不允许一边搭系统，一边临时拍脑袋补估计逻辑。

16. **确认窗口必须基于工程时间基准，而不是自然日口语**
    “当日内确认”在产品上好理解，但实现上必须落到明确规则，例如“probe 后 N 小时内”或“距离市场结算还剩不少于 M 小时”。否则跨时区、晚场比赛和跨日市场会行为漂移。

17. **执行参数必须先过交易所约束校验**
    `probe` 金额、总暴露和退出动作都必须考虑：
    - fee
    - tick size
    - minimum order size
    - reserved balance / available balance
    否则策略参数会在真实执行时失真。

## High-Level Technical Design

### System layout

```text
                     +----------------------+
                     |   Gamma API Poller   |
                     | market discovery     |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     |  Market Selector     |
                     | result window filter |
                     | basic edge filter    |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | Strategy Engine      |
                     | probe / confirm /    |
                     | add / exit / stop    |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | Risk Engine          |
                     | limits + kill switch |
                     | session guard        |
                     +----------+-----------+
                                |
                    allow       |        block
                                |
                                v
                     +----------------------+
                     | CLOB Order Router    |
                     | place/cancel/query   |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | Reconciler           |
                     | orders/fills/pos     |
                     | pnl/session state    |
                     +----------+-----------+
                                |
                +---------------+------------------+
                |                                  |
                v                                  v
   +---------------------------+      +---------------------------+
    | SQLite ledger + read model|      | FastAPI single dashboard |
    | append-only journal       |      | results + status         |
    +---------------------------+      +---------------------------+
```

### Phase-1 strategy slice

```text
Sports winner markets
        |
        v
Result window filter (few days only)
        |
        v
Price-edge filter (obvious only)
        |
        v
Probe with very small size
        |
        +--> not confirmed within same day --> exit
        |
        +--> confirmed --> staged add
                         |
                         +--> weakens again --> reduce/exit
```

### Dependency boundaries

```text
domain
  ^
  |
strategy      risk
  ^            ^
  |            |
  +------ execution ------+
            ^             |
            |             |
      integrations     storage
            ^
            |
           web (read-only from storage/read model)
```

约束：

- `domain` 中不出现 HTTP、数据库、模板、环境变量读取
- `strategy` 不直接 import `gamma_client.py` 或 `clob_client.py`
- `web` 不直接调用交易所 API，不直接拼业务逻辑
- `integrations` 不得写策略判断，只负责协议适配、字段规范化、错误归类

### Trade lifecycle

```text
watching
  |
  | market passes initial filter
  v
probe_pending
  |
  | small order placed
  v
probe_live
  |
  | short confirmation window
  |------------------------------+
  | confirmed                    | not confirmed
  v                              v
confirmed_stage_1             exited_probe
  |
  | add second tranche
  v
confirmed_stage_2
  |
  | hold until exit rule / loss of thesis / near-resolution exit
  v
exited
```

### Session state

```text
RUNNING
  |
  | two probe failures in one session
  v
STOPPED_FOR_DAY
  |
  | next day starts in stricter mode
  v
CAUTIOUS_START
  |
  | first valid confirmation or session passes without issues
  v
RUNNING
```

## Proposed Repository Structure

```text
pyproject.toml
.python-version
.pre-commit-config.yaml
.gitignore
.github/
  workflows/
    ci.yml
.env.example
README.md
docs/
  brainstorms/
  plans/
src/pm_bot/
  config.py
  clocks.py
  app_modes.py
  domain/
    enums.py
    models.py
    value_objects.py
    events.py
  integrations/
    polymarket/
      gamma_client.py
      clob_client.py
      models.py
      translators.py
  strategy/
    market_selector.py
    probe_policy.py
    confirmation_engine.py
    session_guard.py
  risk/
    limits.py
    kill_switch.py
  execution/
    order_router.py
    position_service.py
    reconciler.py
  storage/
    db.py
    schema.py
    migrations/
    repositories.py
    projector.py
  services/
    market_scan_service.py
    trading_loop.py
    pnl_service.py
  web/
    app.py
    templates/
      dashboard.html
tests/
  unit/
  integration/
  architecture/
  fixtures/
```

## Repository Management Rules

### Tooling baseline

- 依赖与虚拟环境：`uv`
- 代码风格与导入排序：`ruff`
- 类型检查：`mypy`
- 测试：`pytest`
- 提交前钩子：`pre-commit`
- CI：GitHub Actions，至少跑 lint + type check + tests

### Branch and commit posture

- 小步提交，优先一单元一提交
- 不允许把“Foundation + Strategy + Web”混成一个大提交
- 第一阶段默认不创建长期分叉模块或实验分支目录

### Environment management

- `.env.example` 必须覆盖所有必需环境变量
- `paper` 与 `live_small` 的配置项必须显式区分
- live 相关环境变量缺失时，系统必须拒绝进入 live_small

### CI gate

最小 CI 成功条件：

1. `ruff` 通过
2. `mypy` 通过
3. `pytest` 单元测试通过
4. 至少一个集成测试分组通过

## Storage Contract

### Ledger and projection model

- `ledger_entries`：append-only，记录所有关键业务事件
- `positions`：从账本和交易所对账得出的当前状态快照
- `session_state`：当日是否收手、是否处于谨慎开局
- `dashboard_snapshot`：首页读取用的投影表，可完全重建

### Migration rules

- schema 变更必须带版本号
- migration 必须先更新 schema，再提供老数据迁移路径
- 任何影响账本语义的变更都必须提供“从历史账本重建 snapshot”的验证

### Replay rules

- 首页 read model 必须支持从空表回放账本完全重建
- 系统启动后如果发现 snapshot 缺失或版本落后，应自动进入重建流程而不是静默继续
- 重放失败时，系统不能进入 live_small

### Single-writer rules

- 只有 `trading_loop` 所在服务可以写业务状态
- `web` 只读
- 调试脚本如果需要修改状态，必须通过明确的 admin/service 接口，不能直接写表

## Translation Boundary

### External to internal model mapping

- `integrations/polymarket/models.py` 只保留外部 DTO
- `integrations/polymarket/translators.py` 负责把外部 DTO 转成内部 `domain` 对象
- `strategy`、`risk`、`execution` 只消费内部对象

### Error normalization

外部错误统一归类为有限集合，例如：

- `temporary_upstream_failure`
- `rate_limited`
- `invalid_order_request`
- `auth_failure`
- `state_mismatch`

这样策略层和风控层不需要理解交易所原始错误文本。

## Phase-1 Default Parameter Posture

这些是第一阶段建议默认值，用于启动 `paper_canary` 和 `small_live_validation`。它们是初始参数，不是永久最优参数。

### Liquidity band

- 默认只保留目标市场流动性落在近 14 天候选集合的 `30th-80th percentile`
- 同时加硬边界，初始建议：
  - 下限：`$20k`
  - 上限：`$250k`

理由：排除太薄、太难成交的市场，也排除最热、最吵、最容易被大资金推动的市场。

### Edge threshold

- 默认要求内部优势信号同时满足：
  - 至少高于最近同类市场普通噪音的 `2x`
  - 且对应的最小优势幅度不低于 `4 个百分点`

说明：
- “4 个百分点”指内部估计胜率与市场隐含概率之间的最小差距
- “2x 噪音”用来防止把普通盘口波动误判成可交易优势
- 该规则只有在“内部估计胜率”已明确定义后才允许启用

### Probe cap

- 单次 `probe` 默认上限：
  - `0.5%` 的验证本金
  - 与 `$20` 固定金额上限取更小者

说明：这让 `probe` 更像测试动作，而不是收益主动作。

### Total market exposure cap

- 单市场总暴露默认上限：
  - `1.5%` 的验证本金
  - 与 `$60` 固定金额上限取更小者

说明：即使 probe 被确认并进入两步加仓，第一阶段也不应让单市场风险过快膨胀。

### Daily loss cap

- 单日最大亏损默认上限：
  - `2.0%` 的验证本金
  - 与 `$75` 固定金额上限取更小者

说明：这属于“普通保守”而不是“神经质”。足够允许正常噪音，但坏环境不能持续吃钱。

### Probe confirmation window

- 产品层口径仍表达为“当日内确认”
- 工程层默认落地为：
  - probe 开启后 `4 小时` 内必须被确认
  - 且距离市场最终结算时间必须仍剩至少 `8 小时`
- 任一条件不满足，则退出或不新开 probe

说明：
- `4 小时` 用来避免 probe 长时间占用资金
- `8 小时` 余量用来避免在过近结算窗口里把短时噪音误当确认

### Exchange execution constraints

- 所有下单金额在进入 execution 前，都必须通过以下校验：
  - 符合市场 `min_order_size`
  - 价格满足市场 `tick_size`
  - 扣除 fee 后仍满足最小经济意义
  - 不突破 reserved balance 与 available balance 约束
- 若任一校验失败，动作应被降级为 `observe_only` 或直接拒绝执行，并记录原因

### Phase-1 estimated win probability interface

- 第一版内部估计胜率**不能**直接从 Polymarket 自身盘口价格反推，否则会形成“用市场价格证明市场价格”的循环。
- 第一版默认采用 `reference probability adapter`，而不是自研体育预测模型：
  - `candidate side` 仍由 Polymarket 盘口和候选筛选逻辑发现
  - `fair win probability` 则来自外部参考概率源，默认是去水位后的 sportsbook / odds consensus snapshot
  - 若外部参考源缺失、过旧或质量不达标，则该候选只能进入 `observe_only`，不得进入 edge 计算和 probe
- 建议接口边界：
  - `src/pm_bot/strategy/reference_probability.py`
  - 输入：`MarketCandidate`、`OrderBookSnapshot`、`as_of`
  - 输出：`EstimatedWinProbability`
- `EstimatedWinProbability` 至少包含：
  - `fair_probability`
  - `source_kind`
  - `source_timestamp`
  - `staleness_seconds`
  - `confidence_band`
  - `is_tradeable`
  - `block_reason`
- 第一版 edge 判断公式应固定为：
  - `edge = fair_probability - market_implied_probability`
  - 只有当 `is_tradeable == true` 且 edge 超过阈值时，候选才允许进入 `probe_policy`
- 第一版估计器的工程要求：
  - 必须可 fixture 化测试，不能只存在于运行时脚本里
  - 必须带 `model_version` 或 `source_version`
  - 必须把“源数据过期”和“无可用参考值”区分开
  - 必须允许后续替换 provider，但当前阶段不抽象成多模型平台

### Recommended external reference probability source

- 默认推荐的第一版 provider：`The Odds API v4`
- 选择理由：
  - 官方文档清楚，`sports / odds / event odds` 路径稳定，便于先做对齐和 fixture
  - 能按 sport、bookmaker、market 拉取标准化 `h2h` 赔率，适合 phase-1 的体育赛果类
  - 官方站点明确提供长期产品与版本化文档，工程上比临时聚合源更适合作为第一版基线
- 明确限制：
  - 免费层只有 `500 credits / month`
  - 这个量级适合 `local_validation` 和窄范围 `paper_canary`
  - 如果后续进入持续运行的 `small_live_validation`，很可能会先撞到额度约束
- 因此第一版建议分阶段使用：
  - `local_validation`：允许直接使用免费层做 fixture 采样与手工验证
  - `paper_canary`：允许低频拉取，严格控制 polling，优先按 event 级别而不是全量 sport 级别刷新
  - `small_live_validation`：保持接口不变，但把“免费额度是否足够”视为上线前单独 gate，而不是现在就强推付费
- 备选而非默认：
  - `odds-api.io` 官方文档和官网都可用，但当前官网免费配额表述存在不一致
  - 因此它适合当备用 provider 研究项，不适合在第一版计划里直接当默认真相源

### Reference odds operating rules

- 第一版只读取 `h2h` 市场，不读取 spreads / totals / player props
- 第一版只维护一个固定 bookmaker 子集，不做动态全市场聚合
  - 默认建议：`draftkings`、`fanduel`、`betmgm`
  - 若 `pinnacle` 在目标 sport / region 可稳定返回，可作为可选第 4 家加入
  - 至少要有 `3` 家 fresh bookmaker 才允许生成 `fair_probability`
- 第一版 fair probability 计算规则：
  - 先把每家 bookmaker 的双边 `h2h` odds 去水位，得到该书自己的 fair probability
  - 再对多家 bookmaker 的 fair probability 取 `median`
  - 不做更复杂的加权、机器学习或动态 bookmaker ranking
- 参考值过期规则：
  - `source_timestamp` 距当前超过 `20 分钟`，视为 stale
  - stale 时允许继续展示，但不允许参与 edge 判定或新开 probe
- 拉取节奏：
  - `local_validation`：允许手动抓样本并固化 fixture，不要求持续 polling
  - `paper_canary`：默认每 `10 分钟` 拉一次 event odds；已有持仓或 probe 中的市场允许缩短到 `5 分钟`
  - `small_live_validation`：沿用同一规则，若额度不足则不上线，而不是偷偷把数据新鲜度放宽
- 请求粒度：
  - 优先使用 event-level odds 拉取，而不是按整项 sport 全量轮询
  - 候选集之外的比赛不主动刷新 reference odds，避免免费额度被背景扫描吃掉
- 额度治理：
  - 每轮抓取都记录 request credits 消耗
  - 连续 24 小时预测的月度消耗若超过预算斜率，系统自动把非持仓市场降级为 `observe_only`
  - 因额度保护触发的降级，必须在 dashboard 状态和日志里显式可见
- fixture 采样规则：
  - 每份 fixture 必须成对保存：
    - `polymarket_candidate_snapshot`
    - `reference_odds_snapshot`
  - 两者必须共享同一个 `as_of` 时间窗口，不允许用不同时间的样本拼接
  - 至少覆盖 3 类样本：
    - 明显优势且最终进入 probe
    - 有一点优势但不足以开 probe
    - 因参考值过期 / 缺失而被降级为 `observe_only`
- paper/live 一致性规则：
  - `reference_probability.py` 在 fixture、paper、small_live 三条路径走同一套变换逻辑
  - 允许变的只有数据来源，不允许变 fair probability 的计算公式

### Phase-1 market semantics freeze

- 第一版不能只写“体育赛果类”，必须冻结为一组明确、可比对的市场语义
- 默认只允许进入 phase-1 的市场：
  - `two-outcome moneyline / h2h` 语义
  - 最终结算不依赖让分、大小分、球员表现、赛段拆分
  - 外部参考赔率能拿到同一语义的二元价格
- 第一版默认排除：
  - 任何可能出现 `Draw` 的三元市场
  - `draw_no_bet`
  - regulation-only 与 overtime-included 语义不一致的市场
  - series winner、tournament winner、futures
  - 改期后结算规则不清晰的特殊市场
- 如果 Polymarket 结算语义与 reference odds 语义不能严格对齐，该市场必须降级为 `observe_only`
- 这条规则的目标不是缩小野心，而是避免把不同玩法硬拼成一条“看起来有 edge”的假信号

### Event identity resolution rules

- 第一版必须有单独的 `event_identity_resolver`，不能把“比赛匹配”散落在 selector 或 client 里临时处理
- 推荐文件边界：
  - `src/pm_bot/strategy/event_identity_resolver.py`
  - `tests/unit/test_event_identity_resolver.py`
- `event_identity_resolver` 的输入：
  - `Polymarket MarketCandidate`
  - `ReferenceOddsEvent`
  - `as_of`
- 输出必须是二选一：
  - `resolved_match`
  - `unmatched_with_reason`
- 第一版唯一允许自动匹配成功的条件：
  - 联赛或 sport key 可映射到同一内部枚举
  - 双方名称在规范化后可稳定双边对应
  - 开赛时间在允许偏差窗口内，默认 `<= 90 分钟`
  - 不存在同一时间窗内多个候选同时满足条件
- 下列情况默认拒绝自动匹配，直接降级为 `observe_only`：
  - 双方顺序不确定
  - 同队名歧义无法消除
  - 延期、改期、双赛或同日多场造成多重候选
  - playoff round / tournament stage 信息不一致
- 事件匹配失败不是异常，而是正常结果；必须被结构化记录到 selection artifact
- 一旦匹配成功并进入 `probe_live` 或形成持仓，resolver 结果必须被持久化到账本与持仓快照：
  - `provider_name`
  - `provider_event_id`
  - `provider_market_type`
  - `matched_home`
  - `matched_away`
  - `matched_start_time`
  - `bookmaker_subset`
  - `match_rule_version`
- 重启恢复后不得重新自由匹配，必须先读取已持久化的 resolver 结果；只有在该结果失效或显式回收后，才允许重新匹配

### Tradable implied probability rules

- 第一版 `market_implied_probability` 必须区分“观察价”和“可成交价”，不能混用
- 默认口径固定如下：
  - 新开 `probe` 或加仓动作，统一按当前**可执行买入价**计算 edge，不能用 mid 或 last trade 代替
  - 减仓或退出动作，统一按当前**可执行卖出价**计算退出经济性
  - `mid` 与 `last_trade_price` 只允许用于监控、噪音估计和 dashboard 展示
- 如果 order book 深度不足以在目标 probe size 上获得稳定可执行价：
  - 不允许因为“表面最优价”而继续下单
  - 应降级为 `observe_only` 或缩小到仍可经济执行的 probe size
- 第一版 edge gate 必须以“扣除 fee 后的可执行隐含概率差”作为最终判定，而不是裸盘口差

### Reference staleness state rules

- 外部参考赔率 stale 之后，不同状态的默认处理必须写死：
  - `watching`：不允许新开 probe，保持 `observe_only`
  - `probe_live`：冻结加仓路径，若在确认窗口内仍未拿到 fresh reference，则按未确认处理退出
  - `confirmed_stage_1`：禁止进入第二段加仓；若 stale 持续到下一次决策窗口，则只允许减仓或退出
  - `confirmed_stage_2`：禁止新增风险，只允许继续持有、减仓或退出，直到 reference 恢复或触发离场规则
- 也就是说，stale 不一定要求立刻平仓，但一定要求：
  - 不再新增风险
  - 不再把旧参考值当成新证据
  - 日志和 dashboard 必须显式可见“参考赔率已过期”

### Clock contract

- 第一版所有跨进程、跨重启的业务时间戳统一使用 `UTC wall clock`
- 第一版所有“经过了多久”的运行时判断统一使用 `monotonic elapsed time`
- 具体约束：
  - `source_timestamp`、`matched_start_time`、结算时间、账本时间戳统一存 UTC
  - `4 小时确认窗口` 的计时逻辑必须基于 monotonic clock，不能直接用本地系统时间差
  - `20 分钟 stale` 判定基于“当前 UTC 时间 - source_timestamp”
- `clocks.py` 必须成为唯一时钟入口，业务层不得直接到处读 `datetime.now()`
- 目标很简单：
  - NTP 跳时不该让 probe 提前或延后结束
  - 时区配置不该改变交易行为
  - 重启后持久化时间仍然可解释

### Wallet isolation rule

- `small_live_validation` 必须使用专用钱包或专用 API 身份，不允许与人工交易或其他 bot 共用
- 这是上线前硬 gate，不是“最佳实践建议”
- 原因：
  - reserved balance 计算依赖 open orders 归属清晰
  - 持仓、PnL、失败恢复和 stop reason 需要唯一归因
  - 否则 reconciliation 会把别的单当成自己的单，整套风控和 dashboard 都会失真
- `paper_canary` 可以使用共享只读数据源，但 `small_live_validation` 的执行身份必须独立

### Exchange constraint read path

- 第一版执行前置校验的读取路径默认固定如下：
  - 市场基础元数据与 token 发现：`Gamma API`
  - `min_order_size`、`tick_size`、`best_bid`、`best_ask`、`last_trade_price`：CLOB `get book(s)` 路径
  - `balance` 与 `allowance`：CLOB L2 `getBalanceAllowance`
  - `reserved balance`：不单独假设为交易所返回字段，而是由 reconciler 基于“交易所未完成订单 + 本地账本状态”计算
  - `fee`：通过官方 fee-rate / client 逻辑读取并缓存到 execution preflight，不允许硬编码成常量
- execution preflight 默认顺序：
  1. 刷新 orderbook summary
  2. 刷新 collateral balance / allowance
  3. 拉取未完成订单并完成本地 reconciliation
  4. 计算 reserved balance
  5. 校验金额、tick、fee 后经济性、available balance
  6. 任一失败则拒绝下单并记结构化原因
- 这条路径的目标不是“尽量把单发出去”，而是保证：
  - 风控看到的余额是真余额
  - 策略看到的可下单量是真可下单量
  - UI 看到的仓位与执行层不漂移

## Implementation Units

### [ ] Unit 0: Establish repository foundation and engineering guardrails

**Requirements trace**
- R8-R11, R26-R30

**Files**
- `pyproject.toml`
- `.python-version`
- `.pre-commit-config.yaml`
- `.gitignore`
- `.github/workflows/ci.yml`
- `.env.example`
- `README.md`

**Test files**
- `tests/architecture/test_dependency_rules.py`
- `tests/unit/test_config.py`

**Approach**
- 用 `uv` 固化 Python 版本和依赖
- 接入 `ruff`、`mypy`、`pytest`、`pre-commit`
- 建立最小 CI
- 写入仓库依赖规则和运行模式约束

**Test scenarios**
- 新增模块违反依赖方向时，架构测试失败
- live_small 缺少任何关键环境变量时，配置校验失败
- CI 在空仓库最小骨架阶段即可跑通

**Verification outcome**
- 仓库在业务代码增长前就具备统一工程纪律

### [ ] Unit 1: Bootstrap runtime foundation, config, and durable state model

**Requirements trace**
- R8-R11, R23-R30

**Files**
- `src/pm_bot/config.py`
- `src/pm_bot/app_modes.py`
- `src/pm_bot/domain/enums.py`
- `src/pm_bot/domain/models.py`
- `src/pm_bot/domain/events.py`
- `src/pm_bot/storage/db.py`
- `src/pm_bot/storage/schema.py`
- `src/pm_bot/storage/projector.py`
- `src/pm_bot/storage/repositories.py`

**Test files**
- `tests/unit/test_domain_models.py`
- `tests/unit/test_storage_schema.py`
- `tests/unit/test_projector.py`

**Approach**
- 建立 `paper` / `live_small` 双模式配置
- 定义核心实体：`MarketCandidate`、`ProbeAttempt`、`TradePosition`、`SessionState`、`DailyRiskState`、`LedgerEntry`
- 建立 append-only 账本表和首页 read model 表
- 约束 live mode 默认关闭，必须显式配置才能启用
- 定义账本事件类型与 projector 重建规则
- 建立 schema version 与 snapshot version 字段

**Test scenarios**
- 缺少 live 所需密钥或风控参数时，系统必须拒绝启动 live mode
- 重启后可以从账本恢复未平仓状态和当日收手状态
- 首页 read model 能从账本正确重建当前总资金、在外仓位和已实现/未实现结果
- snapshot 清空后，系统可以仅依赖账本完成重建
- schema 或 snapshot 版本不匹配时，系统不会静默进入 live_small

**Verification outcome**
- 运行时存在明确的配置边界和可恢复的状态底座

### [ ] Unit 2: Build Polymarket market discovery and candidate selection

**Requirements trace**
- R15-R18, R25

**Files**
- `src/pm_bot/integrations/polymarket/gamma_client.py`
- `src/pm_bot/integrations/polymarket/models.py`
- `src/pm_bot/integrations/polymarket/translators.py`
- `src/pm_bot/strategy/market_selector.py`
- `src/pm_bot/services/market_scan_service.py`

**Test files**
- `tests/unit/test_market_selector.py`
- `tests/unit/test_translators.py`
- `tests/integration/test_gamma_client.py`
- `tests/fixtures/gamma_markets/*.json`

**Approach**
- 从 Gamma API 获取市场和事件元数据
- 通过 translator 把外部 DTO 转换为内部 `MarketCandidate`
- 第一阶段只保留“几天内出结果”的体育赛果类明确事件市场
- 把“热闹但无明显优势”与“值得继续观察”的市场区分开
- 产出结构化候选池，而不是直接出交易指令

**Test scenarios**
- 非体育赛果类市场不会进入第一阶段候选池
- 已过结果窗口、长周期或结果不明确的市场不会进入候选池
- 离结果近但当前无明显优势的市场会被标记为 `observe_only`
- 选择器不会因为单个市场数据异常而让整轮扫描失败
- 外部 API 字段变化不会直接传进 strategy 层对象

**Verification outcome**
- 系统能稳定产出一个窄而可解释的候选市场集合

### [ ] Unit 3: Implement probe / confirmation / session-stop strategy loop

**Requirements trace**
- R19-R25

**Files**
- `src/pm_bot/strategy/probe_policy.py`
- `src/pm_bot/strategy/confirmation_engine.py`
- `src/pm_bot/strategy/session_guard.py`
- `src/pm_bot/strategy/event_identity_resolver.py`
- `src/pm_bot/strategy/reference_probability.py`
- `src/pm_bot/integrations/reference_odds/the_odds_api_client.py`
- `src/pm_bot/integrations/reference_odds/translators.py`
- `src/pm_bot/services/trading_loop.py`

**Test files**
- `tests/unit/test_probe_policy.py`
- `tests/unit/test_confirmation_engine.py`
- `tests/unit/test_session_guard.py`
- `tests/unit/test_event_identity_resolver.py`
- `tests/unit/test_reference_probability.py`
- `tests/integration/test_the_odds_api_client.py`
- `tests/fixtures/reference_odds/*.json`
- `tests/integration/test_trading_loop.py`

**Approach**
- 把机会处理拆成 4 种动作：`observe`、`probe`、`add_stage_1`、`add_stage_2_or_exit`
- 小仓试探进入工程化确认窗口：默认 `4 小时内确认`，且不得晚于“距离市场结算不足 `8 小时`”的边界
- 当天连续 2 次试探未确认后，把 session 状态切为 `STOPPED_FOR_DAY`
- 若前一日为收手状态，次日提高试探触发门槛
- 策略层只消费内部 domain 对象，不直接碰交易所 DTO 或数据库实现
- 第一阶段默认只做“被低估的更强一方”这一类机会，不引入反向做空风格的第二条主线
- 第一版胜率估计器默认使用 `reference probability adapter`：
  - 候选发现仍由 Polymarket 价格触发
  - edge 判定改用外部参考概率与 Polymarket implied probability 的差值
  - 外部参考源缺失或过期时，候选自动降级为 `observe_only`
- 第一版默认外部参考源固定为 `The Odds API v4`
  - 先只读取 `h2h` 市场
  - 先只聚合少量预选 bookmaker，不做全站大范围拉取
  - phase-1 目标是得到稳定 `fair_probability snapshot`，不是做 bookmaker 大而全比较平台
- `event_identity_resolver` 必须先把 Polymarket 比赛与外部 odds event 一一对上，匹配失败则不进入 edge 判定
- edge 的最终门槛必须基于“扣除 fee 后的可执行成交价”，而不是 mid 或 last trade
- 参考赔率 stale 时，不允许新增风险；不同持仓阶段按固定降级规则处理，不能由实现者自由发挥
- phase-1 只允许进入“二元 moneyline / h2h 语义”完全对齐的市场，draw / draw-no-bet / futures 一律排除
- resolver 一旦成功，匹配结果必须持久化并绑定到 probe / position，重启后不得重新自由匹配

**Test scenarios**
- “有一点优势但不够硬”的机会只允许进入 `probe`
- 试探在 `4 小时` 确认窗口内没有被确认时，系统生成退出动作而不是继续持有
- 距离市场结算不足 `8 小时` 时，不会新开需要完整确认窗口的 probe
- 两次试探失败后，当天不会再生成新的 probe 动作
- 次日开局在 `CAUTIOUS_START` 下，试探条件比正常日更严格
- 架构测试确保 strategy 目录不 import integrations 客户端
- 明显优势不足的机会不会进入 probe

**Verification outcome**
- 第一阶段交易节奏被编码成可测试状态机，而不是散落在多个 if/else 里

### [ ] Unit 4: Build execution adapter, reconciliation, and hard risk gates

**Requirements trace**
- R8-R11, R19-R24

**Files**
- `src/pm_bot/integrations/polymarket/clob_client.py`
- `src/pm_bot/risk/limits.py`
- `src/pm_bot/risk/kill_switch.py`
- `src/pm_bot/execution/order_router.py`
- `src/pm_bot/execution/position_service.py`
- `src/pm_bot/execution/reconciler.py`

**Test files**
- `tests/unit/test_limits.py`
- `tests/unit/test_kill_switch.py`
- `tests/unit/test_reconciler.py`
- `tests/integration/test_clob_client.py`
- `tests/integration/test_order_router.py`

**Approach**
- 封装 CLOB 下单、撤单、订单查询、成交查询
- 每次新决策前先对账，确保本地状态与交易所状态一致
- 加入硬风控：
  - 单次 probe 上限默认取 `min(0.5% bankroll, $20)`
  - 单日最大亏损默认取 `min(2.0% bankroll, $75)`
  - 单市场最大总暴露默认取 `min(1.5% bankroll, $60)`
  - kill switch
  - live mode 仅允许 small-live profile
- 明确任何风险校验失败都进入“不下单并记录原因”
- 明确 execution 是唯一业务状态写入入口，统一通过 repository/service 写入账本与投影
- 下单前统一做交易所约束校验：fee、tick size、min order size、reserved balance
- 交易所约束读取路径固定为：
  - `get book(s)` 负责 `min_order_size`、`tick_size`、盘口快照
  - `getBalanceAllowance` 负责 collateral / conditional asset 的余额与授权
  - open orders + fills reconciliation 负责 reserved balance 计算
  - 任意字段刷新失败时，execution 进入 `observe_only`
- `small_live_validation` 默认要求专用钱包或专用 API 身份；若执行身份不独立，则不允许进入真钱验证阶段

**Test scenarios**
- 当日最大亏损达到阈值后，后续动作全部被风险引擎阻断
- kill switch 打开后，即使策略给出信号也不会下单
- 订单部分成交、撤单失败或查询延迟时，对账能把本地状态拉回真实状态
- 重启后第一次循环会先对账，再决定是否恢复交易
- 非交易循环路径无法直接修改核心业务状态
- 下单金额不满足交易所最小下单要求时，动作会被拒绝或降级，不会盲目发送
- 价格不符合 tick size 时，会在 execution 层被规范化或拒绝，并保留原因
- 扣除 fee 后失去经济意义的 probe 不会进入真实下单

**Verification outcome**
- 执行链路不会因为本地误判仓位而继续下单

### [ ] Unit 5: Deliver single-page operator dashboard and stop notification flow

**Requirements trace**
- R26-R30

**Files**
- `src/pm_bot/web/app.py`
- `src/pm_bot/web/templates/dashboard.html`
- `src/pm_bot/services/pnl_service.py`

**Test files**
- `tests/integration/test_dashboard.py`
- `tests/unit/test_pnl_service.py`

**Approach**
- 首页只显示：
  - 当前总资金
  - 今日 / 本周 / 本月盈亏
  - 当前在外仓位
  - 今日已实现 / 未实现
  - 系统状态：`RUNNING` / `STOPPED_FOR_DAY`
- 系统收手时生成一条短结果导向通知
- 不建设第二页，不建设解释型日志浏览器

**Test scenarios**
- 首页在无交易日显示“运行中，暂无达标机会”
- 首页在收手日显示已收手状态和当前结果
- 已实现 / 未实现与账本聚合结果一致

**Verification outcome**
- 用户可以 3 秒读懂系统结果和当前状态

### [ ] Unit 6: Establish phased validation and promotion gates

**Requirements trace**
- R8-R11, Success Criteria

**Files**
- `README.md`
- `docs/plans/2026-04-07-001-feat-polymarket-phase1-validation-bot-plan.md`
- `tests/integration/test_small_live_guards.py`

**Approach**
- 定义三个运行阶段：
  - `local_validation`
  - `paper_canary`
  - `small_live_validation`
- 只有 paper_canary 通过，才允许进入 small_live_validation
- 定义 small-live 通过线：
  - 连续 2 到 3 周运行
  - 达到最小样本数
  - 周/月结果为正
  - 最大回撤不突破预设
  - 重启恢复、对账、收手规则都真实触发过或被验证
- 为每个阶段保存验证工件：
  - daily session summary
  - probe outcome log
  - stop reason summary
  - weekly/monthly pnl snapshot
- 第一阶段通过线默认建立在“低活跃也可接受，只要 2 到 3 周整体赚钱”的前提上，而不是要求大多数天都有交易

**Test scenarios**
- 未满足 paper gate 时，系统不能切换到 live_small
- small-live profile 缺少任何一个硬风控配置时，系统拒绝启动
- promotion gate 计算逻辑不会把少样本好运误判为通过
- 阶段工件缺失时，promotion 不能被判定为通过

**Verification outcome**
- 真实资金验证不会绕过工程门槛

## System-Wide Impact

> Long-term product implication: operator-facing simplicity is not a temporary UI shortcut. It is part of the intended product shape. Even if more earning modes are added later, the user should still primarily experience one machine and one total result.

### Operator-facing impact

- 用户不会看到复杂产品层，只会看到单页结果板和少量状态文案。
- 首页展示的数据必须来自统一账本聚合，否则用户会很快失去信任。

### Runtime impact

- 需要两个长期运行进程：
  - `trading_loop`
  - `web_app`
- 它们共享同一个本地数据库，但只有交易循环负责写入交易状态；Web 只读聚合结果。
- 数据库应启用适合单写多读场景的模式，计划默认按 SQLite WAL 思路设计。

### Security impact

- live mode 会涉及真实钱包 / API 凭证，必须通过环境变量加载，不能写进代码和 fixture。
- kill switch 不能只是 UI 状态，必须进入执行前风险校验链。

### Data integrity impact

- 账本、订单状态、持仓、PnL 聚合必须可重放。
- 任何“已实现 / 未实现 / 当前总资金”都必须从可追溯记录导出，不能只靠内存变量。
- schema 演进不能破坏历史账本回放能力。

## Risks & Dependencies

### Risks

- **市场筛选规则定得太宽**：会把第一阶段做成低质量高噪音交易器  
  Mitigation: 第一阶段先保守筛选，先验证单一场景

- **过早把策略扩成多风格**：会让第一阶段失去可验证性  
  Mitigation: 第一版只做体育赛果 + 价格主导 + 被低估强者主线

- **CLOB 真实状态和本地状态漂移**：会导致重复下单或错判仓位  
  Mitigation: 每轮决策前对账，重启后先对账再交易

- **把短期好运误判为系统能力**：会过早放大资金  
  Mitigation: 建立 paper gate、small-live gate、最小样本数和回撤门槛

- **首页数字不可信**：用户很快会失去系统信任  
  Mitigation: 首页只读账本聚合，不读运行时临时变量

- **模块边界失守**：strategy 直接依赖 API 或数据库细节，后续很快变成泥团  
  Mitigation: 建立依赖规则测试和 translator 反腐层

- **胜率估计器未定就开始实现**：edge 判断会变成漂移目标  
  Mitigation: 将胜率估计器提升为实现前前置设计项

- **自然日口径导致确认窗口漂移**：跨日比赛和时区差异会让同一策略出现不一致行为  
  Mitigation: 用 probe 后小时数 + 距离结算剩余时间作为工程基准

- **策略参数不满足交易所约束**：真实执行时被拒单或经济上不成立  
  Mitigation: execution 层统一校验 fee、tick size、min order size、reserved balance

### Dependencies

- Polymarket Gamma API 可稳定返回市场元数据
- Polymarket CLOB API 和 `py-clob-client` 满足第一阶段读写要求
- 本地环境能安全存放 live mode 所需密钥
- 第一阶段需要明确一个“最值得验证的窄市场类型”，否则策略会重新变宽

## Failure Modes

| Codepath | Realistic failure | Planned test | Error handling | User visibility | Critical gap |
|---|---|---|---|---|---|
| Market scan | Gamma 返回脏数据或单市场字段缺失 | `tests/integration/test_gamma_client.py` | 跳过坏市场并记录错误 | 首页不必提示，日志可见 | no |
| Probe decision | 试探条件误触发，垃圾机会进来 | `tests/unit/test_probe_policy.py` | 仅允许小仓 probe | 结果体现在首页与日志 | no |
| Order placement | 下单成功但本地未记录 | `tests/integration/test_order_router.py` | reconcile before next action | 首页可能短时延迟，但不应静默漂移 | no |
| Reconciliation | 部分成交未被正确合并 | `tests/unit/test_reconciler.py` | 下轮决策前强制对账 | 用户可见仓位/已实现异常 | no |
| Restart recovery | 重启后丢失收手状态或在外仓位 | `tests/integration/test_small_live_guards.py` | 启动先恢复 + 对账 | 首页状态恢复可见 | no |
| PnL aggregation | 已实现/未实现计算错误 | `tests/unit/test_pnl_service.py` | 从账本重算 | 首页数字错误会直接暴露 | no |
| Kill switch | UI 显示已停，但执行层还继续下单 | `tests/unit/test_kill_switch.py` | 执行前风险校验强制检查 | 用户可见已停但会下单，严重 | **yes until implemented** |
| Order economics | probe 金额满足策略条件但不满足 min order / fee / tick 约束 | `tests/integration/test_order_router.py` | execution 前统一约束校验 | 用户通常不可见，但会让策略静默失效 | **yes until implemented** |

当前唯一明确的 **critical gap** 是：kill switch 如果不进入执行链，就会变成装饰。实现时必须优先堵上。

## Test Strategy

### Unit coverage

- 架构依赖方向
- 市场筛选规则
- 试探与确认状态机
- 收手规则
- 风控门槛
- PnL 聚合
- 配置和模式边界

### Integration coverage

- Gamma API 市场抓取与筛选
- CLOB 下单/查单/撤单适配
- 对账流程
- 重启恢复
- 首页聚合结果
- 账本回放与 snapshot 重建

### Manual validation

- `local_validation`: 用 fixture 和模拟数据跑完整状态机
- `paper_canary`: 连续运行同一策略主循环，不真实下单，只写账本
- `small_live_validation`: 小额真钱、强风控、小仓试探、连续 2 到 3 周观察

## Parallelization Strategy

### Dependency table

| Step | Modules touched | Depends on |
|------|----------------|------------|
| Foundation and state model | `src/pm_bot/domain/`, `src/pm_bot/storage/`, config root | — |
| Market discovery and selector | `src/pm_bot/integrations/`, `src/pm_bot/strategy/` | Foundation |
| Strategy loop and session rules | `src/pm_bot/strategy/`, `src/pm_bot/services/` | Foundation, discovery |
| Execution + risk + reconcile | `src/pm_bot/execution/`, `src/pm_bot/risk/`, `src/pm_bot/integrations/` | Foundation |
| Dashboard | `src/pm_bot/web/`, `src/pm_bot/services/`, `src/pm_bot/storage/` | Foundation, execution read model |

### Parallel lanes

- `Lane A`: Foundation and state model → Strategy loop and session rules
- `Lane B`: Foundation and state model → Execution + risk + reconcile
- `Lane C`: Market discovery and selector
- `Lane D`: Dashboard

### Execution order

- 先做 Foundation
- Foundation 完成后，启动 `Lane B` 和 `Lane C`
- `Lane A` 依赖 `Lane C` 的候选市场结构，可以稍后并行推进
- `Lane D` 等待执行层 read model 稳定后再接

### Conflict flags

- `Lane A` 和 `Lane C` 都会触碰 `src/pm_bot/strategy/`，需要顺序协调或明确子模块边界
- `Lane B` 和 `Lane D` 都依赖 `storage` read model，建议由 Foundation 先定义 schema 再并行

## Open Questions

> Requirements alignment note: the long-term goal has now been clarified as "account-level stable money-printing machine / asset-like income line". This changes the framing of later expansion, but does not invalidate the current phase-1 technical skeleton.

### Resolved during planning

- 第一阶段主语言：Python 3.12
- 第一阶段 UI：FastAPI 单页 server-rendered 结果板
- 第一阶段执行模式：paper + live_small 共用同一策略主链路
- 第一阶段策略风格：确定性规则，不把 LLM 放进 live 决策闭环
- 第一阶段环境判定：连续 2 次试探未确认则当天收手
- 仓库工程底座：`uv + ruff + mypy + pytest + pre-commit + GitHub Actions`
- 模块边界：单向依赖 + translator 反腐层 + 单写者数据库规则
- 第一阶段市场类型：体育赛果类
- 第一阶段机会方向：被低估的更强一方
- 第一阶段识别主线：市场价格优先
- 第一阶段价格优势风格：明显但少见
- 第一阶段确认窗口：当日内
- 第一阶段 live_small 风格：严格限额型
- 第一阶段活跃度预期：低活跃可接受，以整体赚钱为准
- 第一阶段流动性过滤风格：中间流动性区间
- 第一阶段参数形式：比例 + 固定金额双保险
- probe 默认上限风格：`min(0.5% bankroll, $20)`
- 单市场总暴露默认风格：`min(1.5% bankroll, $60)`
- 单日亏损默认风格：`min(2.0% bankroll, $75)`
- 优势阈值默认风格：`至少 4 个百分点且高于 2x 普通噪音`
- 确认窗口工程基准：默认 `4 小时确认 + 至少 8 小时结算余量`

### Deferred to implementation

- “普通噪音”的第一版统计口径如何计算
- small-live 通过线里的最小样本数阈值

### Resolved pre-coding decisions for Unit 3 / Unit 4

- 第一版内部估计胜率接口已固定为 `reference probability adapter`
  - 不直接用 Polymarket 自身价格反推 fair probability
  - 默认接收外部参考概率快照，并返回结构化 `EstimatedWinProbability`
  - 没有新鲜、可用的外部参考值时，不做 edge 判定，不开 probe
- 第一版默认外部参考概率 provider 固定为 `The Odds API v4`
  - 当前免费层足够支撑本地验证与低频 paper
  - 是否需要为 `small_live_validation` 升级额度，留作后续上线 gate，不在当前阶段提前花钱
  - 默认 bookmaker 子集为 `draftkings`、`fanduel`、`betmgm`，至少 `3` 家 fresh book 才生成 fair probability
  - 默认 `20 分钟` 过期、`10 分钟` event polling、已有持仓时 `5 分钟` polling
- 第一版默认必须先通过 `event_identity_resolver` 完成 Polymarket 与外部 odds event 的唯一匹配
- edge 默认按“扣 fee 后的可执行价”而不是显示价计算
- reference stale 后禁止新增风险，现有 probe / 持仓按固定降级规则处理
- phase-1 市场语义已冻结为二元 moneyline / h2h，一切 draw / futures / 规则不对齐市场都排除
- resolver 成功结果必须持久化到账本与持仓快照，重启后先读旧绑定，不重新自由匹配
- 时间契约已固定为：持久化时间用 UTC，经过时长用 monotonic
- `small_live_validation` 必须使用专用钱包或专用 API 身份
- 交易所约束字段读取与校验路径已固定为：
  - `Gamma API` 做市场发现
  - `CLOB get book(s)` 读 `min_order_size`、`tick_size`、盘口
  - `getBalanceAllowance` 读 balance / allowance
  - reconciler 基于 open orders + fills 计算 reserved balance
  - execution preflight 统一扣除 fee 并验证最小经济意义

## Language Recommendation

### Recommended

**Python 3.12**

### Why

- Polymarket 有官方 Python CLOB 客户端，第一阶段可以直接接官方能力
- 你的第一阶段重点是策略、规则、验证和风控，不是高并发前端或超低延迟基础设施
- Python 对数据处理、状态机测试、fixture、paper/live 双模式验证更省力
- 用 Python 同时做交易主循环和单页 dashboard，可以把第一阶段复杂度压到最低

### Not recommended for phase 1

- **TypeScript as primary language**  
  不划算。它适合以后做更复杂的前端产品层，但你现在最重要的是策略闭环和真钱验证，不是 Web 产品工程。

- **Rust / Go as primary language**  
  现在太重。第一阶段不是延迟驱动系统，先上这类语言会把时间花在基础设施上，而不是把第一条真钱路径跑出来。

### Revisit point

如果第二阶段以后要做：
- 更复杂的前端产品
- 更高并发的多市场扫描
- 更强的部署和服务拆分

那时再评估是否引入 TypeScript 前端，甚至把执行层独立成另一种语言。第一阶段不建议。

## Next Step

> Updated next step: no additional planning document is required before implementation. When the user authorizes coding, start with `Unit 0` and `Unit 1`, while preserving the long-term governance rule that new complexity is justified only if it moves the system closer to stable, trusted, lower-anxiety income generation.

基于这份方案，下一步应该产出一份更细的实施计划，明确：

1. 第一阶段具体切哪类市场
2. 体育赛果市场里内部估计胜率与“普通噪音”的第一版算法
3. 当日内确认窗口的精确时长与剩余时间阈值
4. Foundation / Strategy / Execution / Dashboard 的落地顺序
