# ADR-0016：API 契约与 OpenAPI 基线

- 状态：Proposed（试运行阶段）
- 背景：与 ADR-0004/0005 保持一致，需要一条“可视化、可比较、低门槛”的 API 契约落地路径，避免早期即引入重型生成链路导致锁死。
- 决策：
  - 对外契约采用 OpenAPI 3.1.0 基线（文件：`openapi/openapi.yaml`）。
  - 进程内（应用内部）继续以 `src/shared/contracts/**` 下的 TypeScript 类型为 SSOT；短期不做 codegen，仅在边界最小化对齐。
  - CI 增加“OpenAPI Diff Summary”非阻断作业：在 Step Summary 展示 paths/operations 统计与前 10 路径清单，并上传 logs/openapi/\*\*。
  - 增加“契约→类型一致性”最小单测（非阻断）：仅校验关键 DTO 的字段名与必填集合，与 TS 合约轮廓一致。
- 影响：
  - 以最小成本建立“契约可视化 + 基本一致性”护栏，减少口径漂移。
  - 避免早期 codegen 带来的强耦合，待接口稳定后再评估 zod/codegen。
  - 当首个端到端用例稳定后，将本 ADR 状态升级为 Accepted。
- 参考：ADR-0004（事件总线与契约）、ADR-0005（质量门禁）
