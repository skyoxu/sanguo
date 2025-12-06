---
ADR-ID: ADR-0007
title: 端口适配器架构 - 六边形架构模式
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, 开发团队]
archRefs: [CH04, CH05, CH06]
verification:
  - path: tests/contract/<port>.spec.ts
    assert: Port contract passes with in-memory adapter
  - path: scripts/arch/madge-check.mjs
    assert: No reversed dependencies or cycles across domain boundaries
  - path: tests/unit/retries.spec.ts
    assert: Timeout/retry/idempotency policies are enforced
impact-scope:
  - src/ports/
  - src/adapters/
  - src/domain/
  - src/shared/contracts/
tech-tags:
  - hexagonal-architecture
  - ports-adapters
  - dependency-injection
  - interfaces
depends-on: []
depended-by: []
test-coverage: tests/unit/adr-0007.spec.ts
monitoring-metrics:
  - implementation_coverage
  - compliance_rate
executable-deliverables:
  - src/ports/GameEnginePort.ts
  - src/adapters/PhaserGameAdapter.ts
  - tests/unit/architecture/ports-adapters.spec.ts
supersedes: []
---

# ADR-0007: 端口适配器架构（六边形架构）

## Context and Problem Statement

游戏应用需要与多种外部系统交互（数据库、文件系统、网络服务、Electron APIs），同时保持核心业务逻辑的独立性和可测试性。需要建立清晰的架构边界，使得业务逻辑不依赖于具体的技术实现，便于测试、维护和技术栈变更。

## Decision Drivers

- 需要将业务逻辑与外部依赖解耦
- 需要提高代码的可测试性和可维护性
- 需要支持不同的技术栈适配（SQLite、文件系统、网络等）
- 需要明确的架构边界和职责分离
- 需要支持领域驱动设计（DDD）原则
- 需要便于单元测试和集成测试
- 需要支持依赖注入和控制反转

## Considered Options

- **六边形架构（端口-适配器）** (选择方案)
- **分层架构（传统三层架构）**
- **洋葱架构（Clean Architecture）**
- **微服务架构（过度工程）**
- **模块化单体架构**

## Decision Outcome

选择的方案：**六边形架构（端口-适配器模式）**

### 架构核心概念

**六边形架构层次划分**：

```
┌─────────────────────────────────────────────────────────┐
│                    外部世界                                │
│  ┌─────────────────────────────────────────────────┐    │
│  │                  适配器层                         │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │                应用层                     │    │    │
│  │  │  ┌─────────────────────────────────┐    │    │    │
│  │  │  │            领域层                 │    │    │    │
│  │  │  │  - 实体 (Entities)              │    │    │    │
│  │  │  │  - 值对象 (Value Objects)       │    │    │    │
│  │  │  │  - 领域服务 (Domain Services)   │    │    │    │
│  │  │  └─────────────────────────────────┘    │    │    │
│  │  │                                         │    │    │
│  │  │  - 应用服务 (Application Services)      │    │    │
│  │  │  - 端口接口 (Ports)                    │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  │                                                 │    │
│  │  - 适配器实现 (Adapters)                         │    │
│  │  - 基础设施 (Infrastructure)                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  - 用户接口 (UI)                                         │
│  - 外部服务 (External Services)                         │
└─────────────────────────────────────────────────────────┘
```

### 端口定义（Ports）

**输入端口（Primary Ports）**：

```typescript
// src/core/ports/primary/game-service.port.ts
export interface GameServicePort {
  startNewGame(
    playerId: string,
    gameConfig: GameConfiguration
  ): Promise<GameSession>;
  loadGame(saveId: string): Promise<GameSession>;
  saveGame(session: GameSession): Promise<void>;
  pauseGame(sessionId: string): Promise<void>;
  resumeGame(sessionId: string): Promise<void>;
}

// src/core/ports/primary/player-service.port.ts
export interface PlayerServicePort {
  createPlayer(playerData: CreatePlayerRequest): Promise<Player>;
  getPlayer(playerId: string): Promise<Player>;
  updatePlayer(playerId: string, updates: UpdatePlayerRequest): Promise<Player>;
  levelUp(playerId: string, experience: number): Promise<LevelUpResult>;
  addAchievement(playerId: string, achievementId: string): Promise<void>;
}

// src/core/ports/primary/inventory-service.port.ts
export interface InventoryServicePort {
  addItem(playerId: string, item: GameItem, quantity: number): Promise<void>;
  removeItem(playerId: string, itemId: string, quantity: number): Promise<void>;
  getInventory(playerId: string): Promise<PlayerInventory>;
  equipItem(
    playerId: string,
    itemId: string,
    slotType: EquipmentSlot
  ): Promise<void>;
  unequipItem(playerId: string, slotType: EquipmentSlot): Promise<void>;
}
```

**输出端口（Secondary Ports）**：

```typescript
// src/core/ports/secondary/game-repository.port.ts
export interface GameRepositoryPort {
  findById(gameId: string): Promise<GameSave | null>;
  save(gameSave: GameSave): Promise<void>;
  findByPlayerId(playerId: string): Promise<GameSave[]>;
  delete(gameId: string): Promise<void>;
}

// src/core/ports/secondary/player-repository.port.ts
export interface PlayerRepositoryPort {
  findById(playerId: string): Promise<Player | null>;
  save(player: Player): Promise<void>;
  findByUsername(username: string): Promise<Player | null>;
  updateStats(playerId: string, stats: PlayerStats): Promise<void>;
}

// src/core/ports/secondary/file-system.port.ts
export interface FileSystemPort {
  readFile(filePath: string): Promise<string>;
  writeFile(filePath: string, content: string): Promise<void>;
  exists(filePath: string): Promise<boolean>;
  deleteFile(filePath: string): Promise<void>;
  createDirectory(dirPath: string): Promise<void>;
}

// src/core/ports/secondary/event-publisher.port.ts
export interface EventPublisherPort {
  publish<T extends CloudEventExtended>(event: T): Promise<void>;
  subscribe<T extends CloudEventExtended>(
    eventType: string,
    handler: (event: T) => Promise<void>
  ): () => void;
}
```

### 领域层实现

**实体（Entities）**：

```typescript
// src/core/domain/entities/player.entity.ts
export class Player {
  constructor(
    private readonly id: PlayerId,
    private name: PlayerName,
    private level: PlayerLevel,
    private experience: Experience,
    private stats: PlayerStats,
    private inventory: PlayerInventory,
    private achievements: Achievement[]
  ) {}

  public levelUp(experienceGained: number): LevelUpResult {
    const newExperience = this.experience.add(experienceGained);
    const newLevel = this.calculateLevelFromExperience(newExperience);

    const result = new LevelUpResult(
      this.level,
      newLevel,
      experienceGained,
      this.getUnlockedSkills(newLevel)
    );

    this.experience = newExperience;
    this.level = newLevel;

    return result;
  }

  public addAchievement(achievement: Achievement): void {
    if (this.hasAchievement(achievement.id)) {
      throw new DomainError('Player already has this achievement');
    }

    this.achievements.push(achievement);
  }

  public canEquipItem(item: GameItem, slot: EquipmentSlot): boolean {
    return (
      this.level.value >= item.requiredLevel &&
      this.stats.meets(item.requirements) &&
      this.inventory.canEquip(item, slot)
    );
  }

  // 不变性保护
  private calculateLevelFromExperience(experience: Experience): PlayerLevel {
    const level = Math.floor(experience.value / 1000) + 1;
    return new PlayerLevel(Math.min(level, 100)); // 最大等级100
  }

  private hasAchievement(achievementId: AchievementId): boolean {
    return this.achievements.some(a => a.id.equals(achievementId));
  }

  // 访问器
  public getId(): PlayerId {
    return this.id;
  }
  public getName(): PlayerName {
    return this.name;
  }
  public getLevel(): PlayerLevel {
    return this.level;
  }
  public getExperience(): Experience {
    return this.experience;
  }
}
```

**值对象（Value Objects）**：

```typescript
// src/core/domain/value-objects/player-id.vo.ts
export class PlayerId {
  constructor(private readonly value: string) {
    if (!value || value.trim().length === 0) {
      throw new DomainError('Player ID cannot be empty');
    }
    if (!/^[a-zA-Z0-9-_]+$/.test(value)) {
      throw new DomainError('Player ID contains invalid characters');
    }
  }

  public getValue(): string {
    return this.value;
  }

  public equals(other: PlayerId): boolean {
    return this.value === other.value;
  }

  public toString(): string {
    return this.value;
  }
}

// src/core/domain/value-objects/experience.vo.ts
export class Experience {
  constructor(private readonly value: number) {
    if (value < 0) {
      throw new DomainError('Experience cannot be negative');
    }
    if (value > 1000000) {
      throw new DomainError('Experience cannot exceed 1,000,000');
    }
  }

  public add(amount: number): Experience {
    return new Experience(this.value + amount);
  }

  public subtract(amount: number): Experience {
    return new Experience(Math.max(0, this.value - amount));
  }

  public getValue(): number {
    return this.value;
  }

  public equals(other: Experience): boolean {
    return this.value === other.value;
  }
}
```

**领域服务（Domain Services）**：

```typescript
// src/core/domain/services/level-calculation.service.ts
export class LevelCalculationService {
  private static readonly EXPERIENCE_TABLE = [
    0, 1000, 2500, 4500, 7000, 10000, 14000, 19000, 25000, 32000, 40000,
    // ... 更多等级经验需求
  ];

  public calculateLevel(experience: Experience): PlayerLevel {
    const exp = experience.getValue();
    let level = 1;

    for (
      let i = LevelCalculationService.EXPERIENCE_TABLE.length - 1;
      i >= 0;
      i--
    ) {
      if (exp >= LevelCalculationService.EXPERIENCE_TABLE[i]) {
        level = i + 1;
        break;
      }
    }

    return new PlayerLevel(level);
  }

  public getExperienceForLevel(level: PlayerLevel): Experience {
    const levelValue = level.getValue();
    if (
      levelValue <= 0 ||
      levelValue > LevelCalculationService.EXPERIENCE_TABLE.length
    ) {
      throw new DomainError('Invalid level');
    }

    return new Experience(
      LevelCalculationService.EXPERIENCE_TABLE[levelValue - 1]
    );
  }

  public getExperienceToNextLevel(
    experience: Experience,
    currentLevel: PlayerLevel
  ): Experience {
    const nextLevel = currentLevel.getValue() + 1;
    if (nextLevel > LevelCalculationService.EXPERIENCE_TABLE.length) {
      return new Experience(0); // 已达最高等级
    }

    const nextLevelExp =
      LevelCalculationService.EXPERIENCE_TABLE[nextLevel - 1];
    const remaining = nextLevelExp - experience.getValue();
    return new Experience(Math.max(0, remaining));
  }
}
```

### 应用层实现

**应用服务（Application Services）**：

```typescript
// src/core/application/services/player-application.service.ts
export class PlayerApplicationService implements PlayerServicePort {
  constructor(
    private readonly playerRepository: PlayerRepositoryPort,
    private readonly eventPublisher: EventPublisherPort,
    private readonly levelCalculationService: LevelCalculationService
  ) {}

  public async createPlayer(request: CreatePlayerRequest): Promise<Player> {
    // 验证输入
    if (!request.username || !request.email) {
      throw new ApplicationError('Username and email are required');
    }

    // 检查用户名是否已存在
    const existingPlayer = await this.playerRepository.findByUsername(
      request.username
    );
    if (existingPlayer) {
      throw new ApplicationError('Username already exists');
    }

    // 创建玩家实体
    const player = new Player(
      new PlayerId(generateId()),
      new PlayerName(request.username),
      new PlayerLevel(1),
      new Experience(0),
      PlayerStats.createDefault(),
      PlayerInventory.createEmpty(),
      []
    );

    // 持久化
    await this.playerRepository.save(player);

    // 发布领域事件
    await this.eventPublisher.publish({
      id: generateEventId(),
      source: 'game.player',
      type: 'com.buildgame.player.created',
      specversion: '1.0',
      time: new Date().toISOString(),
      data: {
        playerId: player.getId().getValue(),
        username: player.getName().getValue(),
        createdAt: new Date().toISOString(),
      },
    });

    return player;
  }

  public async levelUp(
    playerId: string,
    experienceGained: number
  ): Promise<LevelUpResult> {
    const player = await this.playerRepository.findById(playerId);
    if (!player) {
      throw new ApplicationError('Player not found');
    }

    const levelUpResult = player.levelUp(experienceGained);
    await this.playerRepository.save(player);

    // 发布升级事件
    await this.eventPublisher.publish({
      id: generateEventId(),
      source: 'game.player',
      type: 'com.buildgame.player.levelup',
      specversion: '1.0',
      time: new Date().toISOString(),
      data: {
        playerId: player.getId().getValue(),
        previousLevel: levelUpResult.previousLevel.getValue(),
        newLevel: levelUpResult.newLevel.getValue(),
        experienceGained: experienceGained,
        unlockedSkills: levelUpResult.unlockedSkills,
      },
    });

    return levelUpResult;
  }

  public async getPlayer(playerId: string): Promise<Player> {
    const player = await this.playerRepository.findById(playerId);
    if (!player) {
      throw new ApplicationError('Player not found');
    }
    return player;
  }
}
```

### 适配器层实现

**数据库适配器**：

```typescript
// src/infrastructure/adapters/secondary/sqlite-player-repository.adapter.ts
export class SQLitePlayerRepositoryAdapter implements PlayerRepositoryPort {
  constructor(private readonly dbManager: SQLiteManager) {}

  public async findById(playerId: string): Promise<Player | null> {
    const db = this.dbManager.getDatabase();
    const stmt = db.prepare('SELECT * FROM players WHERE id = ?');
    const row = stmt.get(playerId);

    if (!row) return null;

    return this.mapRowToPlayer(row);
  }

  public async save(player: Player): Promise<void> {
    const db = this.dbManager.getDatabase();

    const playerData = {
      id: player.getId().getValue(),
      name: player.getName().getValue(),
      level: player.getLevel().getValue(),
      experience: player.getExperience().getValue(),
      stats: JSON.stringify(player.getStats().toJSON()),
      inventory: JSON.stringify(player.getInventory().toJSON()),
      achievements: JSON.stringify(
        player.getAchievements().map(a => a.toJSON())
      ),
    };

    const stmt = db.prepare(`
      INSERT OR REPLACE INTO players (id, name, level, experience, stats, inventory, achievements, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    `);

    stmt.run(
      playerData.id,
      playerData.name,
      playerData.level,
      playerData.experience,
      playerData.stats,
      playerData.inventory,
      playerData.achievements
    );
  }

  private mapRowToPlayer(row: any): Player {
    return new Player(
      new PlayerId(row.id),
      new PlayerName(row.name),
      new PlayerLevel(row.level),
      new Experience(row.experience),
      PlayerStats.fromJSON(JSON.parse(row.stats)),
      PlayerInventory.fromJSON(JSON.parse(row.inventory)),
      JSON.parse(row.achievements).map(Achievement.fromJSON)
    );
  }
}
```

**文件系统适配器**：

```typescript
// src/infrastructure/adapters/secondary/electron-file-system.adapter.ts
export class ElectronFileSystemAdapter implements FileSystemPort {
  constructor(private readonly app: Electron.App) {}

  public async readFile(filePath: string): Promise<string> {
    try {
      const fullPath = this.resolvePath(filePath);
      return await fs.readFile(fullPath, 'utf-8');
    } catch (error) {
      throw new InfrastructureError(`Failed to read file: ${filePath}`, error);
    }
  }

  public async writeFile(filePath: string, content: string): Promise<void> {
    try {
      const fullPath = this.resolvePath(filePath);
      await fs.ensureDir(path.dirname(fullPath));
      await fs.writeFile(fullPath, content, 'utf-8');
    } catch (error) {
      throw new InfrastructureError(`Failed to write file: ${filePath}`, error);
    }
  }

  public async exists(filePath: string): Promise<boolean> {
    try {
      const fullPath = this.resolvePath(filePath);
      await fs.access(fullPath);
      return true;
    } catch {
      return false;
    }
  }

  private resolvePath(filePath: string): string {
    if (path.isAbsolute(filePath)) {
      return filePath;
    }
    return path.join(this.app.getPath('userData'), filePath);
  }
}
```

**用户界面适配器**：

```typescript
// src/infrastructure/adapters/primary/http-game-controller.adapter.ts
export class HttpGameControllerAdapter {
  constructor(private readonly gameService: GameServicePort) {}

  public async handleStartGame(req: Request, res: Response): Promise<void> {
    try {
      const { playerId, gameConfig } = req.body;

      const gameSession = await this.gameService.startNewGame(
        playerId,
        gameConfig
      );

      res.json({
        success: true,
        data: {
          sessionId: gameSession.getId(),
          playerId: gameSession.getPlayerId(),
          startedAt: gameSession.getStartTime(),
        },
      });
    } catch (error) {
      this.handleError(res, error);
    }
  }

  private handleError(res: Response, error: any): void {
    if (error instanceof ApplicationError) {
      res.status(400).json({ success: false, error: error.message });
    } else if (error instanceof DomainError) {
      res.status(422).json({ success: false, error: error.message });
    } else {
      res.status(500).json({ success: false, error: 'Internal server error' });
    }
  }
}
```

### 依赖注入配置

**依赖容器配置**：

```typescript
// src/infrastructure/di/container.ts
import { Container } from 'inversify';
import { TYPES } from './types';

const container = new Container();

// 绑定端口到适配器
container
  .bind<PlayerRepositoryPort>(TYPES.PlayerRepository)
  .to(SQLitePlayerRepositoryAdapter)
  .inSingletonScope();

container
  .bind<GameRepositoryPort>(TYPES.GameRepository)
  .to(SQLiteGameRepositoryAdapter)
  .inSingletonScope();

container
  .bind<FileSystemPort>(TYPES.FileSystem)
  .to(ElectronFileSystemAdapter)
  .inSingletonScope();

container
  .bind<EventPublisherPort>(TYPES.EventPublisher)
  .to(CloudEventBusAdapter)
  .inSingletonScope();

// 绑定应用服务
container
  .bind<PlayerServicePort>(TYPES.PlayerService)
  .to(PlayerApplicationService)
  .inSingletonScope();

container
  .bind<GameServicePort>(TYPES.GameService)
  .to(GameApplicationService)
  .inSingletonScope();

// 绑定领域服务
container
  .bind<LevelCalculationService>(TYPES.LevelCalculationService)
  .to(LevelCalculationService)
  .inSingletonScope();

export { container };
```

### In-Memory适配器（测试隔离）

为CI环境和单元测试提供的内存适配器实现，遵循相同的端口契约：

**内存仓储适配器**：

```typescript
// src/infrastructure/adapters/secondary/in-memory-player-repository.adapter.ts
export class InMemoryPlayerRepositoryAdapter implements PlayerRepositoryPort {
  private players: Map<string, Player> = new Map();

  public async findById(playerId: string): Promise<Player | null> {
    return this.players.get(playerId) || null;
  }

  public async save(player: Player): Promise<void> {
    this.players.set(player.getId().getValue(), player);
  }

  public async findByName(playerName: string): Promise<Player | null> {
    for (const player of this.players.values()) {
      if (player.getName().getValue() === playerName) {
        return player;
      }
    }
    return null;
  }

  // 测试辅助方法
  public clear(): void {
    this.players.clear();
  }

  public size(): number {
    return this.players.size;
  }
}
```

**内存文件系统适配器**：

```typescript
// src/infrastructure/adapters/secondary/in-memory-filesystem.adapter.ts
export class InMemoryFileSystemAdapter implements FileSystemPort {
  private files: Map<string, string> = new Map();

  public async readFile(filePath: string): Promise<string> {
    const content = this.files.get(filePath);
    if (!content) {
      throw new Error(`File not found: ${filePath}`);
    }
    return content;
  }

  public async writeFile(filePath: string, content: string): Promise<void> {
    this.files.set(filePath, content);
  }

  public async exists(filePath: string): Promise<boolean> {
    return this.files.has(filePath);
  }

  public async deleteFile(filePath: string): Promise<void> {
    this.files.delete(filePath);
  }

  // 测试辅助方法
  public clear(): void {
    this.files.clear();
  }

  public getAllFiles(): Record<string, string> {
    return Object.fromEntries(this.files.entries());
  }
}
```

**测试配置容器**：

```typescript
// src/infrastructure/container/test.container.ts
export const testContainer = new Container();

// 使用In-Memory适配器进行测试隔离
testContainer
  .bind<PlayerRepositoryPort>(TYPES.PlayerRepository)
  .to(InMemoryPlayerRepositoryAdapter)
  .inSingletonScope();

testContainer
  .bind<FileSystemPort>(TYPES.FileSystem)
  .to(InMemoryFileSystemAdapter)
  .inSingletonScope();

// 其他服务保持不变
testContainer
  .bind<PlayerServicePort>(TYPES.PlayerService)
  .to(PlayerApplicationService)
  .inSingletonScope();
```

**测试用例示例**：

```typescript
// tests/unit/application/services/player.service.spec.ts
describe('PlayerApplicationService', () => {
  let playerService: PlayerServicePort;
  let playerRepository: InMemoryPlayerRepositoryAdapter;

  beforeEach(() => {
    // 使用测试容器隔离外部依赖
    playerRepository = testContainer.get<PlayerRepositoryPort>(
      TYPES.PlayerRepository
    ) as InMemoryPlayerRepositoryAdapter;
    playerService = testContainer.get<PlayerServicePort>(TYPES.PlayerService);

    // 清理测试数据
    playerRepository.clear();
  });

  it('should level up player when sufficient experience', async () => {
    // 完全隔离的测试环境，无需真实数据库
    const player = new Player(
      new PlayerId('test-123'),
      new PlayerName('TestPlayer')
    );
    await playerRepository.save(player);

    const result = await playerService.levelUpPlayer('test-123', 1500);

    expect(result.newLevel.getValue()).toBe(2);
    expect(playerRepository.size()).toBe(1);
  });
});
```

### Positive Consequences

- 业务逻辑与技术实现完全解耦，提高可维护性
- 优秀的可测试性，可以轻松进行单元测试和集成测试
- 支持不同技术栈的适配器替换，增强灵活性
- 明确的架构边界和职责分离
- 支持领域驱动设计原则，业务逻辑清晰表达
- 依赖注入使得组件组装更加灵活
- 便于实现横切关注点（日志、缓存、事务等）

### Negative Consequences

- 初期架构设计复杂度较高，学习成本增加
- 需要编写更多的接口和适配器代码
- 依赖注入框架增加了额外的复杂性
- 小型项目可能存在过度设计的问题
- 调试时需要理解架构层次关系
- 性能开销轻微增加（主要是抽象层调用）

## Verification

- **测试验证**: tests/unit/domain/entities/_.spec.ts, tests/integration/adapters/_.spec.ts
- **门禁脚本**: scripts/verify_architecture_boundaries.mjs, scripts/check_dependency_direction.mjs
- **监控指标**: architecture.coupling_metrics, dependencies.violation_count, tests.coverage_by_layer
- **架构验证**: 依赖方向检查、端口-适配器边界验证、领域纯度检查

### 架构验证清单

- [ ] 依赖方向正确（外层依赖内层，内层不依赖外层）
- [ ] 领域层不包含任何基础设施依赖
- [ ] 应用层仅依赖端口接口，不依赖具体适配器
- [ ] 适配器正确实现端口接口
- [ ] 实体和值对象保持不变性和业务规则
- [ ] 领域服务不包含应用逻辑
- [ ] 依赖注入配置正确且完整

## Operational Playbook

### 升级步骤

1. **架构分层**: 按照六边形架构原则组织代码结构
2. **端口定义**: 定义所有输入端口和输出端口接口
3. **领域实现**: 实现实体、值对象和领域服务
4. **应用服务**: 实现应用服务和用例编排
5. **适配器实现**: 实现各种技术适配器
6. **依赖注入**: 配置依赖注入容器和绑定关系

### 回滚步骤

1. **架构简化**: 如遇复杂性问题，可临时简化架构层次
2. **直接依赖**: 紧急情况下可允许直接依赖绕过端口
3. **适配器降级**: 回退到简单的适配器实现
4. **容器禁用**: 临时禁用依赖注入，使用直接实例化
5. **边界放松**: 临时允许跨层直接调用

### 迁移指南

- **代码重构**: 现有代码需要按照架构层次重新组织
- **接口抽取**: 将具体实现抽象为端口接口
- **依赖反转**: 调整依赖方向，实现控制反转
- **测试重写**: 按照架构层次重写单元测试和集成测试
- **团队培训**: 团队需要学习六边形架构和DDD原则

## References

- **CH章节关联**: CH04, CH05, CH06
- **相关ADR**: ADR-0006-data-storage, ADR-0004-event-bus-and-contracts, ADR-0005-quality-gates
- **外部文档**:
  - [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
  - [Ports and Adapters Pattern](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
  - [Domain-Driven Design](https://domainlanguage.com/ddd/)
  - [Dependency Inversion Principle](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- **架构模式**: Clean Architecture, Onion Architecture, Hexagonal Architecture
- **相关PRD-ID**: 适用于所有需要业务逻辑清晰分离的PRD模块
