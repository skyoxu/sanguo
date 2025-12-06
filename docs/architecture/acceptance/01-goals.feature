Feature: 01 目标与SLO落地
  Scenario: SLO/门禁映射已配置
    Given 工程已包含 gates 配置
    Then 应存在 crash_free、tp95、coverage 三类门禁
    And crash_free 阈值不低于 99.5%