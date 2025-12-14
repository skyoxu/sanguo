# 一句话先总结

## 必看做“参考”的：

Paulemeister/monopoly_clone – 看“大富翁格子/地产/收租”的玩法拆法。

hermannm/casus-belli – 看 Godot 4 + C# 项目结构、领域层怎么和 Godot 节点交互。

C7-Game/Prototype（OpenCiv3） – 看回合制+年月日时间轴+经济系统的组织方式。

## 按 PRD 里的模块，一一配对参考仓库

### 1.棋盘 / 城池 / 环形路线
PRD：一条环形路线，节点是三国城池，维护城池列表、所属州郡、价格等。

#### 推荐参考：

- ✅ Paulemeister/monopoly_clone

  - 用来看：

    - 它怎么表示“格子 / 地块 / 事件格 / 监狱格”这类东西；

    - 玩家站在格子上时，买地 / 收租 / 无事发生的状态机；

    - Godot 里格子和逻辑的关联思路（Tile → 数据 + 节点）。

  - 用法建议：

    只学设计，不拷代码：因为看不见明确 LICENSE，很可能默认保留版权，适合当“参考思路”。

- ✅ Loupine/multiplayer-board-game（多人棋盘模板，GDScript，可选）

    - 虽然你现在是单机，但它有：

      - 回合+棋盘+单位的基本组织；

      - “一个格一层抽象”的思想；

    - 用法：看一下它的棋盘节点树、格子数据结构，帮你决定自己 Board / City 的粒度即可。

实际落地：
你的 GitHub 仓库里建议自己写：

  - Board / GameMap：List<City> + 环形下标计算；

  - City：Name / Region / BasePrice / BaseToll / Owner / BaseYield。
这块逻辑很轻，不需要引第三方库。

### 2.回合制 + “天 → 月 → 季度 → 年”时间轴
PRD：每回合 = 1 天，月底结算，季度事件，年初地价调整。

#### 推荐参考：

- ✅ C7-Game/Prototype（OpenCiv3）

    - 重点看：

        - 它怎么表示“回合数、年份、回合推进”的；

        - 有没有类似日历 / 时代 / 年份的封装；

        - 大型回合制项目里，“回合管理器 + 经济系统 + 事件系统”怎么拆到不同类里。

    - 对你来说，最有价值的是把“时间系统”单独抽成服务，而不是写死在场景脚本。

- ✅ hermannm/casus-belli

    - 侧重点稍微不同：

        - 看它如何在 C# 里组织“回合/状态机 + Godot 场景”的；

        - 客户端是 Godot 4 + C#，你的技术栈完全对口。

    - 你可以仿照它的方式把：

        - TurnManager（当前玩家/当前日）

        - GameState（年/月/日/玩家列表）

        - 放在 Core 层，Godot 只负责展示。

实际落地：
你的项目里要自己新建：

  - TurnManager：管理“谁的回合＋推进一天”的状态机；

  - GameCalendar 或直接在 GameState 里扩展 Year/Month/Day + helper 方法；

  - EconomyService / TimeService：负责在日历变动时触发：

    - 月末结算，

    - 季度事件生成，

    - 年初地价调整。

这几块都可以借 OpenCiv3 的思想，但用你自己的类名和结构实现。

### 3. 地产 / 收租 / 经济结算 / 环境事件

PRD：

  - 每城池 = 一块地；

  - 谁踩谁付钱；

  - 每月底按城池产出结算；

  - 季度环境事件改收益；

  - 年初统一地价调整。

#### 推荐参考：

- ✅ Paulemeister/monopoly_clone

    - 用来对应你 PRD 中的：

        - “买地 / 不买”交互；

        - “收租算法”；

        - 玩家资金更新 + UI提示。

    - 你要自己再加：

        - “月产”概念；

        - “受环境事件影响的收益系数”。

- ✅ C7-Game/Prototype（OpenCiv3）

    - 看它的“经济系统 / 资源产出 / 回合结算”模块：

        - 类似的“每回合 / 每几回合做一次结算”的结构；

        - 单独的经济 manager 类，利用 GameState 做汇总。

实际落地：
在你的 Core 里做：

  - EconomyManager：

    - SettleMonth()：遍历所有玩家→玩家的 OwnedCities→算产出；

    - AdjustPricesOnNewYear()：遍历所有 City 调整价格相关字段；

  - EventManager：

    - 季度触发“某州郡收益 x1.5 / x0.5”等；

    - GetYieldModifierFor(City) 给 EconomyManager 用。

这些仓库给的是参考模式，实现得按你 PRD 的时间节奏重新写。

### 4. 棋子移动 / 网格引擎

PRD：路线是环形单线，没有复杂寻路。

实际落地：
建议自己写一个小类/方法就够了：

int GetNextPositionIndex(int currentIndex, int steps, int cityCount)
    => (currentIndex + steps) % cityCount;


然后用 Godot Tween 把棋子从 City[currentIndex].WorldPosition 移动到 City[newIndex].WorldPosition。

### 5. AI 行为

PRD：AI 只需要：

  - 自动掷骰子；

  - 有钱就买地；

  - 踩到别人的地自动付钱。

这里几个开源项目里的 AI 都比较“硬核”（Civ 那种），而你 T2 的需求是非常简单的贪心逻辑，反而自己写最快。

  - 你可以参考：

    - OpenCiv3 / MiniX 中 AI 策略是如何被隔离成一个“决策层”的（State → Decision → Action）；

    - 但实际逻辑 T2 可以简单写成：

        - if (canAfford(city.Price) && ShouldBuy(city)) Buy();

        - ShouldBuy 里先写死 true，后面再慢慢变聪明。

结论：AI 不需要任何外部框架，自己写就好。

### 6. UI / 掷骰效果 / 视觉糖

PRD：T2 对 UI 要求不高，能看清信息即可。

可选参考（非必需）：

3D Dice Roller Template

如果你以后想做一个很爽的掷骰动画，可以用它的思路；

但你现在是 2D 游戏，T2 完全可以用简单的数字+轻微动画，没必要引这个。

### 最后帮你归档成“需要用到的仓库清单”

你可以这样写到 tasks master / 规划里：

#### 高优先级（阅读 + 参考）

  - Paulemeister/monopoly_clone

    参考内容：格子/地块/地产结构，买地 & 收租逻辑，玩家资金更新模式。

  - hermannm/casus-belli

    参考内容：Godot 4 + C# 项目结构，领域层与 Godot Node/Scene 的连接方式，回合制客户端组织。

  - C7-Game/Prototype（OpenCiv3）

    参考内容：回合制时间轴（Turn → Year/Month/Day）的设计，经济系统管理（产出 & 结算）模式。