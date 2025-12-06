Feature: 02 Electron 安全基线
  Scenario: 基线护栏启用
    Given 应用以生产配置启动
    Then 渲染进程应禁用 Node 能力
    And 存在严格 CSP 元标签
