Feature: 02 Godot 安全基线
  Scenario: 基线护栏启用
    Given 应用以安全配置启动（GD_SECURE_MODE=1）
    Then 仅允许 res:// 读取与 user:// 写入
    And 外链仅允许 https 且主机必须在 ALLOWED_EXTERNAL_HOSTS 白名单中
