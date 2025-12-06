---
ADR-ID: ADR-0010
title: 国际化策略 - i18next + 动态语言切换
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, UX团队, 国际化团队]
archRefs: [CH01, CH06, CH10]
verification:
  - path: src/i18n/index.ts
    assert: i18next configured with fallbackLng, namespaces, and lazy loading
  - path: tests/e2e/i18n.spec.ts
    assert: Language switch updates <html lang|dir> and localized formatters + RTL CSS styles verification
  - path: scripts/i18n/keys-check.mjs
    assert: All locale files have identical keys and no missing translations
impact-scope:
  - src/i18n/
  - locales/
  - src/components/
tech-tags:
  - i18n
  - i18next
  - localization
  - internationalization
depends-on: []
depended-by: []
test-coverage: tests/unit/adr-0010.spec.ts
monitoring-metrics:
  - implementation_coverage
  - compliance_rate
executable-deliverables:
  - src/i18n/config.ts
  - locales/en/translation.json
  - tests/unit/i18n/translation.spec.ts
supersedes: []
---

# ADR-0010: 国际化与本地化策略

## Context and Problem Statement

Build Game需要支持多语言和多地区，提供本地化的用户体验。需要建立可扩展的国际化架构，支持动态语言切换、复数形式处理、日期时间格式化、文本方向性（RTL/LTR）和文化敏感内容适配。同时需要考虑Electron应用的特殊性，确保主进程和渲染进程的语言设置同步。

## Decision Drivers

- 需要支持至少6种语言（中文简体、中文繁体、英语、日语、韩语、德语）
- 需要动态语言切换，无需重启应用
- 需要支持复数形式和语法变化
- 需要本地化日期、时间、数字、货币格式
- 需要支持从右到左（RTL）语言如阿拉伯语
- 需要延迟加载语言包，减少初始化时间
- 需要与Electron主进程语言设置同步
- 需要支持插件和扩展的国际化

## Considered Options

- **react-i18next + 命名空间 + 懒加载** (选择方案)
- **Format.js (React Intl) + 分包加载**
- **自定义i18n引擎 + JSON语言包**
- **Electron locales API + React context**
- **第三方云端翻译服务集成**

## Decision Outcome

选择的方案：**react-i18next + 命名空间 + 懒加载**

### 核心配置与初始化

**i18next配置**：

```typescript
// src/shared/i18n/config.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

export const SUPPORTED_LANGUAGES = {
  'zh-CN': { name: '中文（简体）', flag: '🇨🇳', rtl: false },
  'zh-TW': { name: '中文（繁體）', flag: '🇹🇼', rtl: false },
  en: { name: 'English', flag: '🇺🇸', rtl: false },
  ja: { name: '日本語', flag: '🇯🇵', rtl: false },
  ko: { name: '한국어', flag: '🇰🇷', rtl: false },
  de: { name: 'Deutsch', flag: '🇩🇪', rtl: false },
  ar: { name: 'العربية', flag: '🇸🇦', rtl: true },
} as const;

export const DEFAULT_NAMESPACE = 'common';
export const FALLBACK_LANGUAGE = 'en';

const i18nConfig = {
  fallbackLng: FALLBACK_LANGUAGE,
  defaultNS: DEFAULT_NAMESPACE,

  // 命名空间配置
  ns: [
    'common', // 通用词汇：按钮、标签、状态
    'game', // 游戏内容：角色、装备、技能
    'ui', // 界面组件：菜单、对话框、提示
    'settings', // 设置页面：选项、配置、偏好
    'errors', // 错误消息：验证、网络、系统
    'onboarding', // 引导流程：教程、提示、帮助
  ],

  // 懒加载配置
  partialBundledLanguages: true,

  // 语言检测配置
  detection: {
    order: ['localStorage', 'navigator', 'htmlTag'],
    lookupLocalStorage: 'i18nextLng',
    caches: ['localStorage'],
  },

  // 后端配置（懒加载）
  backend: {
    loadPath: '/locales/{{lng}}/{{ns}}.json',
    addPath: '/locales/add/{{lng}}/{{ns}}',
    allowMultiLoading: false,
  },

  // React配置
  react: {
    useSuspense: true,
    bindI18n: 'languageChanged loaded',
    bindI18nStore: 'added removed',
    transEmptyNodeValue: '',
    transSupportBasicHtmlNodes: true,
    transKeepBasicHtmlNodesFor: ['br', 'strong', 'i', 'p'],
  },

  // 插值配置
  interpolation: {
    escapeValue: false, // React已经防XSS
    formatSeparator: ',',
    format: function (value, format, lng) {
      if (format === 'uppercase') return value.toUpperCase();
      if (format === 'lowercase') return value.toLowerCase();
      if (value instanceof Date) return formatDateTime(value, format, lng);
      if (typeof value === 'number') return formatNumber(value, format, lng);
      return value;
    },
  },

  // 开发配置
  debug: process.env.NODE_ENV === 'development',

  // 资源加载超时
  load: 'languageOnly',
  preload: [FALLBACK_LANGUAGE],

  // 键值分隔符
  keySeparator: '.',
  nsSeparator: ':',

  // 复数规则
  pluralSeparator: '_',
  contextSeparator: '_',
};

i18n.use(Backend).use(LanguageDetector).use(initReactI18next).init(i18nConfig);

export default i18n;
```

**语言包结构**：

```json
// public/locales/zh-CN/common.json
{
  "buttons": {
    "confirm": "确认",
    "cancel": "取消",
    "save": "保存",
    "delete": "删除",
    "edit": "编辑",
    "add": "添加"
  },
  "labels": {
    "name": "名称",
    "description": "描述",
    "type": "类型",
    "status": "状态",
    "created": "创建时间",
    "updated": "更新时间"
  },
  "status": {
    "loading": "加载中...",
    "success": "成功",
    "error": "错误",
    "warning": "警告",
    "pending": "等待中"
  },
  "validation": {
    "required": "此字段为必填项",
    "minLength": "最少需要{{min}}个字符",
    "maxLength": "最多允许{{max}}个字符",
    "email": "请输入有效的邮箱地址",
    "phone": "请输入有效的手机号码"
  }
}

// public/locales/zh-CN/game.json
{
  "character": {
    "level": "等级",
    "experience": "经验值",
    "health": "生命值",
    "mana": "魔法值",
    "strength": "力量",
    "agility": "敏捷",
    "intelligence": "智力"
  },
  "inventory": {
    "items_one": "{{count}}件物品",
    "items_other": "{{count}}件物品",
    "capacity": "容量：{{current}}/{{max}}",
    "empty": "背包为空",
    "full": "背包已满"
  },
  "skills": {
    "attack": "攻击",
    "defense": "防御",
    "magic": "魔法",
    "healing": "治疗",
    "buff": "增益效果",
    "debuff": "减益效果"
  }
}
```

### React组件集成

**Hook封装**：

```typescript
// src/shared/i18n/hooks.ts
import { useTranslation } from 'react-i18next';
import { useCallback, useMemo } from 'react';
import { SUPPORTED_LANGUAGES } from './config';

export interface UseI18nReturn {
  t: (key: string, options?: any) => string;
  currentLanguage: string;
  currentLanguageInfo: (typeof SUPPORTED_LANGUAGES)[keyof typeof SUPPORTED_LANGUAGES];
  supportedLanguages: typeof SUPPORTED_LANGUAGES;
  changeLanguage: (lng: string) => Promise<void>;
  isRTL: boolean;
  formatDateTime: (date: Date, format?: string) => string;
  formatNumber: (num: number, format?: string) => string;
  formatCurrency: (amount: number, currency?: string) => string;
}

export function useI18n(namespace?: string | string[]): UseI18nReturn {
  const { t, i18n } = useTranslation(namespace);

  const currentLanguage = i18n.language;
  const currentLanguageInfo = useMemo(
    () =>
      SUPPORTED_LANGUAGES[
        currentLanguage as keyof typeof SUPPORTED_LANGUAGES
      ] || SUPPORTED_LANGUAGES.en,
    [currentLanguage]
  );

  const changeLanguage = useCallback(
    async (lng: string) => {
      await i18n.changeLanguage(lng);
      // 同步到Electron主进程
      if (window.electronAPI) {
        await window.electronAPI.setLanguage(lng);
      }
      // 更新HTML lang属性
      document.documentElement.lang = lng;
      document.documentElement.dir = SUPPORTED_LANGUAGES[
        lng as keyof typeof SUPPORTED_LANGUAGES
      ]?.rtl
        ? 'rtl'
        : 'ltr';
    },
    [i18n]
  );

  const formatDateTime = useCallback(
    (date: Date, format = 'short'): string => {
      const locale =
        currentLanguage === 'zh-CN'
          ? 'zh-CN'
          : currentLanguage === 'zh-TW'
            ? 'zh-TW'
            : currentLanguage;

      const options: Intl.DateTimeFormatOptions =
        {
          short: {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          },
          date: {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          },
          time: {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          },
          relative: {
            numeric: 'auto',
          },
        }[format] || {};

      if (format === 'relative') {
        const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
        const diffTime = date.getTime() - new Date().getTime();
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return rtf.format(diffDays, 'day');
      }

      return new Intl.DateTimeFormat(locale, options).format(date);
    },
    [currentLanguage]
  );

  const formatNumber = useCallback(
    (num: number, format = 'decimal'): string => {
      const locale = currentLanguage;
      const options: Intl.NumberFormatOptions =
        {
          decimal: { maximumFractionDigits: 2 },
          integer: { maximumFractionDigits: 0 },
          percent: { style: 'percent', maximumFractionDigits: 1 },
          compact: { notation: 'compact', maximumFractionDigits: 1 },
        }[format] || {};

      return new Intl.NumberFormat(locale, options).format(num);
    },
    [currentLanguage]
  );

  const formatCurrency = useCallback(
    (amount: number, currency = 'USD'): string => {
      const locale = currentLanguage;
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
      }).format(amount);
    },
    [currentLanguage]
  );

  return {
    t,
    currentLanguage,
    currentLanguageInfo,
    supportedLanguages: SUPPORTED_LANGUAGES,
    changeLanguage,
    isRTL: currentLanguageInfo.rtl,
    formatDateTime,
    formatNumber,
    formatCurrency,
  };
}

// 命名空间特化Hook
export const useCommonI18n = () => useI18n('common');
export const useGameI18n = () => useI18n('game');
export const useUIi18n = () => useI18n('ui');
export const useSettingsI18n = () => useI18n('settings');
export const useErrorsI18n = () => useI18n('errors');
```

**语言切换组件**：

```typescript
// src/components/common/LanguageSwitcher.tsx
import React, { Suspense } from 'react';
import { useI18n } from '../../shared/i18n/hooks';

export interface LanguageSwitcherProps {
  variant?: 'dropdown' | 'buttons' | 'compact';
  showFlags?: boolean;
  className?: string;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  variant = 'dropdown',
  showFlags = true,
  className = ''
}) => {
  const {
    currentLanguage,
    supportedLanguages,
    changeLanguage,
    t
  } = useI18n();

  const handleLanguageChange = async (lng: string) => {
    try {
      await changeLanguage(lng);
      // 可选：显示切换成功提示
    } catch (error) {
      console.error('Language change failed:', error);
      // 可选：显示错误提示
    }
  };

  if (variant === 'dropdown') {
    return (
      <div className={`language-switcher ${className}`}>
        <label htmlFor="language-select" className="sr-only">
          {t('settings.language')}
        </label>
        <select
          id="language-select"
          value={currentLanguage}
          onChange={(e) => handleLanguageChange(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          data-testid="language-switcher"
        >
          {Object.entries(supportedLanguages).map(([code, info]) => (
            <option key={code} value={code}>
              {showFlags ? `${info.flag} ${info.name}` : info.name}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (variant === 'buttons') {
    return (
      <div className={`language-buttons flex gap-2 ${className}`}>
        {Object.entries(supportedLanguages).map(([code, info]) => (
          <button
            key={code}
            onClick={() => handleLanguageChange(code)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              currentLanguage === code
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            data-testid={`language-button-${code}`}
          >
            {showFlags ? `${info.flag} ${info.name}` : info.name}
          </button>
        ))}
      </div>
    );
  }

  // Compact variant
  return (
    <div className={`language-compact ${className}`}>
      <button
        onClick={() => {
          const languages = Object.keys(supportedLanguages);
          const currentIndex = languages.indexOf(currentLanguage);
          const nextIndex = (currentIndex + 1) % languages.length;
          handleLanguageChange(languages[nextIndex]);
        }}
        className="flex items-center gap-2 px-2 py-1 text-sm hover:bg-gray-100 rounded"
        data-testid="language-toggle"
      >
        {showFlags && supportedLanguages[currentLanguage as keyof typeof supportedLanguages].flag}
        <span>{currentLanguage.toUpperCase()}</span>
      </button>
    </div>
  );
};

// Suspense包装器，处理懒加载
export const LanguageSwitcherWithSuspense: React.FC<LanguageSwitcherProps> = (props) => {
  return (
    <Suspense fallback={<div className="w-20 h-8 bg-gray-200 animate-pulse rounded"></div>}>
      <LanguageSwitcher {...props} />
    </Suspense>
  );
};
```

### Electron集成

**主进程语言同步**：

```typescript
// electron/i18n.ts
import { app, ipcMain } from 'electron';
import * as path from 'path';
import * as fs from 'fs';

export class ElectronI18nManager {
  private currentLanguage: string;
  private supportedLanguages = ['zh-CN', 'zh-TW', 'en', 'ja', 'ko', 'de', 'ar'];

  constructor() {
    this.currentLanguage = this.detectSystemLanguage();
    this.setupIpcHandlers();
  }

  private detectSystemLanguage(): string {
    const systemLocale = app.getLocale();
    const normalizedLocale = this.normalizeLocale(systemLocale);

    return this.supportedLanguages.includes(normalizedLocale)
      ? normalizedLocale
      : 'en';
  }

  private normalizeLocale(locale: string): string {
    // 处理系统语言代码到应用语言代码的映射
    const localeMap: Record<string, string> = {
      zh: 'zh-CN',
      'zh-CN': 'zh-CN',
      'zh-TW': 'zh-TW',
      'zh-HK': 'zh-TW',
      en: 'en',
      'en-US': 'en',
      'en-GB': 'en',
      ja: 'ja',
      ko: 'ko',
      de: 'de',
      ar: 'ar',
    };

    return localeMap[locale] || 'en';
  }

  private setupIpcHandlers(): void {
    ipcMain.handle('i18n:get-language', () => {
      return this.currentLanguage;
    });

    ipcMain.handle('i18n:set-language', (event, language: string) => {
      if (this.supportedLanguages.includes(language)) {
        this.currentLanguage = language;

        // 更新应用菜单语言
        this.updateAppMenu();

        // 保存到用户设置
        this.saveLanguagePreference(language);

        // 广播语言变更事件
        event.sender.webContents.getAllFrames().forEach(frame => {
          frame.send('i18n:language-changed', language);
        });

        return { success: true, language };
      }

      return { success: false, error: 'Unsupported language' };
    });

    ipcMain.handle('i18n:get-system-locale', () => {
      return {
        system: app.getLocale(),
        detected: this.detectSystemLanguage(),
        country: app.getLocaleCountryCode(),
      };
    });
  }

  private updateAppMenu(): void {
    // 根据当前语言更新应用菜单
    // 这里需要重新构建菜单模板
    const menuTemplate = this.buildLocalizedMenuTemplate();
    // 应用新菜单...
  }

  private buildLocalizedMenuTemplate(): Electron.MenuItemConstructorOptions[] {
    const translations = this.loadMainProcessTranslations();

    return [
      {
        label: translations.file || 'File',
        submenu: [
          {
            label: translations.new || 'New',
            accelerator: 'CmdOrCtrl+N',
          },
          {
            label: translations.open || 'Open',
            accelerator: 'CmdOrCtrl+O',
          },
          { type: 'separator' },
          {
            label: translations.quit || 'Quit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            role: 'quit',
          },
        ],
      },
      {
        label: translations.edit || 'Edit',
        submenu: [
          {
            label: translations.undo || 'Undo',
            accelerator: 'CmdOrCtrl+Z',
            role: 'undo',
          },
          {
            label: translations.redo || 'Redo',
            accelerator: 'Shift+CmdOrCtrl+Z',
            role: 'redo',
          },
          { type: 'separator' },
          {
            label: translations.cut || 'Cut',
            accelerator: 'CmdOrCtrl+X',
            role: 'cut',
          },
          {
            label: translations.copy || 'Copy',
            accelerator: 'CmdOrCtrl+C',
            role: 'copy',
          },
          {
            label: translations.paste || 'Paste',
            accelerator: 'CmdOrCtrl+V',
            role: 'paste',
          },
        ],
      },
    ];
  }

  private loadMainProcessTranslations(): Record<string, string> {
    try {
      const translationPath = path.join(
        __dirname,
        '../locales',
        this.currentLanguage,
        'electron.json'
      );
      const translations = JSON.parse(fs.readFileSync(translationPath, 'utf8'));
      return translations.menu || {};
    } catch (error) {
      console.warn(
        `Failed to load main process translations for ${this.currentLanguage}:`,
        error
      );
      return {};
    }
  }

  private saveLanguagePreference(language: string): void {
    // 保存语言偏好到用户配置文件
    const userDataPath = app.getPath('userData');
    const configPath = path.join(userDataPath, 'i18n-config.json');

    try {
      const config = {
        language,
        lastUpdated: new Date().toISOString(),
      };
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    } catch (error) {
      console.error('Failed to save language preference:', error);
    }
  }

  public getCurrentLanguage(): string {
    return this.currentLanguage;
  }
}
```

**预加载脚本API**：

```typescript
// electron/preload.ts (添加i18n相关API)
import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  // ... 其他API ...

  // 国际化API
  i18n: {
    getLanguage: () => ipcRenderer.invoke('i18n:get-language'),
    setLanguage: (language: string) =>
      ipcRenderer.invoke('i18n:set-language', language),
    getSystemLocale: () => ipcRenderer.invoke('i18n:get-system-locale'),
    onLanguageChanged: (callback: (language: string) => void) => {
      ipcRenderer.on('i18n:language-changed', (event, language) =>
        callback(language)
      );
    },
    removeLanguageChangedListener: () => {
      ipcRenderer.removeAllListeners('i18n:language-changed');
    },
  },
});
```

### 复数形式处理

**复数规则配置**：

```typescript
// src/shared/i18n/plural-rules.ts
export const PLURAL_RULES = {
  'zh-CN': {
    cardinal: ['other'],
    ordinal: ['other'],
  },
  'zh-TW': {
    cardinal: ['other'],
    ordinal: ['other'],
  },
  en: {
    cardinal: ['one', 'other'],
    ordinal: ['one', 'two', 'few', 'other'],
  },
  ja: {
    cardinal: ['other'],
    ordinal: ['other'],
  },
  ko: {
    cardinal: ['other'],
    ordinal: ['other'],
  },
  de: {
    cardinal: ['one', 'other'],
    ordinal: ['other'],
  },
  ar: {
    cardinal: ['zero', 'one', 'two', 'few', 'many', 'other'],
    ordinal: ['other'],
  },
};

// 复数形式使用示例
export const usePluralExamples = () => {
  const { t } = useI18n();

  return {
    // 英语：1 item / 5 items
    // 中文：1 个物品 / 5 个物品
    items: (count: number) => t('game:inventory.items', { count }),

    // 英语：1st level / 2nd level / 3rd level / 4th level
    // 中文：第 1 级 / 第 2 级
    level: (num: number) => t('game:character.level_ordinal', { ordinal: num }),

    // 阿拉伯语复杂复数形式
    // 0 items / 1 item / 2 items / 3-10 items / 11+ items
    arabicItems: (count: number) => t('game:inventory.items_ar', { count }),
  };
};
```

**语言包复数示例**：

```json
// public/locales/en/game.json
{
  "inventory": {
    "items_one": "{{count}} item",
    "items_other": "{{count}} items"
  },
  "character": {
    "level_ordinal_1": "{{ordinal}}st level",
    "level_ordinal_2": "{{ordinal}}nd level",
    "level_ordinal_3": "{{ordinal}}rd level",
    "level_ordinal_other": "{{ordinal}}th level"
  }
}

// public/locales/zh-CN/game.json
{
  "inventory": {
    "items_other": "{{count}} 个物品"
  },
  "character": {
    "level_ordinal_other": "第 {{ordinal}} 级"
  }
}

// public/locales/ar/game.json
{
  "inventory": {
    "items_zero": "لا توجد عناصر",
    "items_one": "عنصر واحد",
    "items_two": "عنصران",
    "items_few": "{{count}} عناصر",
    "items_many": "{{count}} عنصراً",
    "items_other": "{{count}} عنصر"
  }
}
```

### 测试策略

**国际化测试套件**：

```typescript
// tests/unit/i18n/i18n.spec.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import i18n from '../../../src/shared/i18n/config';
import { useI18n } from '../../../src/shared/i18n/hooks';
import { renderHook, act } from '@testing-library/react';

describe('Internationalization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Language Detection', () => {
    it('should detect browser language correctly', async () => {
      Object.defineProperty(window.navigator, 'language', {
        value: 'zh-CN',
        writable: true,
      });

      await i18n.init();
      expect(i18n.language).toBe('zh-CN');
    });

    it('should fallback to English for unsupported languages', async () => {
      Object.defineProperty(window.navigator, 'language', {
        value: 'fr-FR',
        writable: true,
      });

      await i18n.init();
      expect(i18n.language).toBe('en');
    });
  });

  describe('Language Switching', () => {
    it('should switch language and update HTML attributes', async () => {
      const { result } = renderHook(() => useI18n());

      await act(async () => {
        await result.current.changeLanguage('zh-CN');
      });

      expect(result.current.currentLanguage).toBe('zh-CN');
      expect(document.documentElement.lang).toBe('zh-CN');
      expect(document.documentElement.dir).toBe('ltr');
    });

    it('should handle RTL languages correctly', async () => {
      const { result } = renderHook(() => useI18n());

      await act(async () => {
        await result.current.changeLanguage('ar');
      });

      expect(result.current.isRTL).toBe(true);
      expect(document.documentElement.dir).toBe('rtl');
    });
  });

  describe('Pluralization', () => {
    it('should handle English plurals correctly', async () => {
      await i18n.changeLanguage('en');

      expect(i18n.t('game:inventory.items', { count: 1 })).toBe('1 item');
      expect(i18n.t('game:inventory.items', { count: 5 })).toBe('5 items');
    });

    it('should handle Chinese plurals correctly', async () => {
      await i18n.changeLanguage('zh-CN');

      expect(i18n.t('game:inventory.items', { count: 1 })).toBe('1 个物品');
      expect(i18n.t('game:inventory.items', { count: 5 })).toBe('5 个物品');
    });

    it('should handle Arabic complex plurals', async () => {
      await i18n.changeLanguage('ar');

      expect(i18n.t('game:inventory.items', { count: 0 })).toBe(
        'لا توجد عناصر'
      );
      expect(i18n.t('game:inventory.items', { count: 1 })).toBe('عنصر واحد');
      expect(i18n.t('game:inventory.items', { count: 2 })).toBe('عنصران');
      expect(i18n.t('game:inventory.items', { count: 5 })).toBe('5 عناصر');
    });
  });

  describe('Date and Number Formatting', () => {
    it('should format dates according to locale', () => {
      const { result } = renderHook(() => useI18n());
      const testDate = new Date('2025-01-15T10:30:00Z');

      act(() => {
        result.current.changeLanguage('zh-CN');
      });

      const formatted = result.current.formatDateTime(testDate, 'date');
      expect(formatted).toContain('2025');
      expect(formatted).toContain('1');
      expect(formatted).toContain('15');
    });

    it('should format numbers according to locale', () => {
      const { result } = renderHook(() => useI18n());

      act(() => {
        result.current.changeLanguage('de');
      });

      const formatted = result.current.formatNumber(1234.56, 'decimal');
      expect(formatted).toBe('1.234,56'); // German formatting
    });

    it('should format currency according to locale', () => {
      const { result } = renderHook(() => useI18n());

      act(() => {
        result.current.changeLanguage('en');
      });

      const formatted = result.current.formatCurrency(1234.56, 'USD');
      expect(formatted).toBe('$1,234.56');
    });
  });

  describe('Namespace Loading', () => {
    it('should load namespace lazily', async () => {
      const loadSpy = vi.spyOn(i18n.services.backendConnector, 'load');

      await i18n.loadNamespaces('settings');

      expect(loadSpy).toHaveBeenCalledWith(
        ['en'],
        ['settings'],
        expect.any(Function)
      );
    });

    it('should cache loaded namespaces', async () => {
      await i18n.loadNamespaces('common');
      const loadSpy = vi.spyOn(i18n.services.backendConnector, 'load');

      await i18n.loadNamespaces('common'); // Second load

      expect(loadSpy).not.toHaveBeenCalled(); // Should be cached
    });
  });
});
```

**E2E国际化测试**：

```typescript
// tests/e2e/i18n.electron.spec.ts
import { test, expect, _electron as electron } from '@playwright/test';

test.describe('Internationalization E2E', () => {
  let app: any;
  let window: any;

  test.beforeAll(async () => {
    app = await electron.launch({
      args: ['./electron/main.js'],
      timeout: 10000,
    });

    window = await app.firstWindow();
    await window.waitForLoadState('domcontentloaded');
  });

  test.afterAll(async () => {
    await app.close();
  });

  test('should display interface in system language', async () => {
    // 验证界面使用系统语言
    const title = await window
      .locator('[data-testid="app-title"]')
      .textContent();
    expect(title).toBeTruthy();
  });

  test('should switch language through settings', async () => {
    // 打开设置页面
    await window.locator('[data-testid="settings-button"]').click();
    await expect(
      window.locator('[data-testid="settings-panel"]')
    ).toBeVisible();

    // 切换到中文
    await window
      .locator('[data-testid="language-switcher"]')
      .selectOption('zh-CN');

    // 等待语言切换完成
    await window.waitForTimeout(1000);

    // 验证界面已切换到中文
    const settingsTitle = await window
      .locator('[data-testid="settings-title"]')
      .textContent();
    expect(settingsTitle).toContain('设置');

    // 验证HTML lang属性已更新
    const htmlLang = await window.evaluate(() => document.documentElement.lang);
    expect(htmlLang).toBe('zh-CN');
  });

  test('should handle RTL languages correctly', async () => {
    // 切换到阿拉伯语
    await window
      .locator('[data-testid="language-switcher"]')
      .selectOption('ar');
    await window.waitForTimeout(1000);

    // 验证文档方向已变更为RTL
    const htmlDir = await window.evaluate(() => document.documentElement.dir);
    expect(htmlDir).toBe('rtl');

    // 🆕 验证CSS样式是否正确响应RTL布局
    const bodyElement = window.locator('body');
    await expect(bodyElement).toHaveCSS('direction', 'rtl');

    // 验证关键UI元素的RTL CSS布局
    const mainContent = window.locator('[data-testid="main-content"]');
    await expect(mainContent).toHaveCSS('text-align', 'right');

    // 验证导航菜单RTL布局
    const navMenu = window.locator('[data-testid="nav-menu"]');
    await expect(navMenu).toHaveCSS('direction', 'rtl');

    // 验证阿拉伯语文本显示
    const title = await window
      .locator('[data-testid="app-title"]')
      .textContent();
    expect(title).toContain('العاب'); // Arabic text

    // 🆕 验证Flexbox布局在RTL下的正确性
    const flexContainer = window.locator('[data-testid="flex-container"]');
    if ((await flexContainer.count()) > 0) {
      await expect(flexContainer).toHaveCSS(
        'flex-direction',
        /row-reverse|column/
      );
    }
  });

  test('should format dates according to selected locale', async () => {
    // 切换到德语
    await window
      .locator('[data-testid="language-switcher"]')
      .selectOption('de');
    await window.waitForTimeout(1000);

    // 查看日期格式
    const dateElement = await window.locator('[data-testid="current-date"]');
    const dateText = await dateElement.textContent();

    // 德语日期格式应该是 DD.MM.YYYY
    expect(dateText).toMatch(/\d{1,2}\.\d{1,2}\.\d{4}/);
  });

  test('should persist language choice across app restarts', async () => {
    // 设置语言为日语
    await window
      .locator('[data-testid="language-switcher"]')
      .selectOption('ja');
    await window.waitForTimeout(1000);

    // 重启应用
    await app.close();
    app = await electron.launch({
      args: ['./electron/main.js'],
      timeout: 10000,
    });
    window = await app.firstWindow();
    await window.waitForLoadState('domcontentloaded');

    // 验证语言设置被保持
    const htmlLang = await window.evaluate(() => document.documentElement.lang);
    expect(htmlLang).toBe('ja');
  });
});
```

### CI/CD集成

**国际化验证脚本**：

```javascript
// scripts/verify_i18n.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const LOCALES_DIR = path.join(__dirname, '../public/locales');
const SUPPORTED_LANGUAGES = ['zh-CN', 'zh-TW', 'en', 'ja', 'ko', 'de', 'ar'];
const REQUIRED_NAMESPACES = [
  'common',
  'game',
  'ui',
  'settings',
  'errors',
  'onboarding',
];

class I18nValidator {
  constructor() {
    this.errors = [];
    this.warnings = [];
  }

  async validate() {
    console.log('🌐 Validating internationalization...');

    await this.validateDirectoryStructure();
    await this.validateLanguageFiles();
    await this.validateKeyConsistency();
    await this.validatePlurals();

    this.reportResults();

    if (this.errors.length > 0) {
      process.exit(1);
    }
  }

  async validateDirectoryStructure() {
    for (const lang of SUPPORTED_LANGUAGES) {
      const langDir = path.join(LOCALES_DIR, lang);
      if (!fs.existsSync(langDir)) {
        this.errors.push(`Missing language directory: ${lang}`);
        continue;
      }

      for (const namespace of REQUIRED_NAMESPACES) {
        const filePath = path.join(langDir, `${namespace}.json`);
        if (!fs.existsSync(filePath)) {
          this.errors.push(`Missing namespace file: ${lang}/${namespace}.json`);
        }
      }
    }
  }

  async validateLanguageFiles() {
    for (const lang of SUPPORTED_LANGUAGES) {
      for (const namespace of REQUIRED_NAMESPACES) {
        const filePath = path.join(LOCALES_DIR, lang, `${namespace}.json`);
        if (!fs.existsSync(filePath)) continue;

        try {
          const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
          await this.validateJsonStructure(
            content,
            `${lang}/${namespace}.json`
          );
        } catch (error) {
          this.errors.push(
            `Invalid JSON in ${lang}/${namespace}.json: ${error.message}`
          );
        }
      }
    }
  }

  async validateJsonStructure(obj, filePath, keyPath = '') {
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = keyPath ? `${keyPath}.${key}` : key;

      if (typeof value === 'object' && value !== null) {
        await this.validateJsonStructure(value, filePath, fullKey);
      } else if (typeof value === 'string') {
        // 验证插值变量
        const interpolations = value.match(/\{\{[\w.]+\}\}/g) || [];
        for (const interpolation of interpolations) {
          const varName = interpolation.slice(2, -2);
          if (!varName.match(/^[\w.]+$/)) {
            this.warnings.push(
              `Invalid interpolation variable "${varName}" in ${filePath}:${fullKey}`
            );
          }
        }

        // 验证HTML标签
        const htmlTags = value.match(/<[^>]+>/g) || [];
        for (const tag of htmlTags) {
          if (!tag.match(/^<(br|strong|i|p|\/?(br|strong|i|p))>$/)) {
            this.warnings.push(
              `Potentially unsafe HTML tag "${tag}" in ${filePath}:${fullKey}`
            );
          }
        }
      }
    }
  }

  async validateKeyConsistency() {
    const referenceKeys = new Map();

    // 使用英语作为参考
    for (const namespace of REQUIRED_NAMESPACES) {
      const filePath = path.join(LOCALES_DIR, 'en', `${namespace}.json`);
      if (fs.existsSync(filePath)) {
        const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        const keys = this.extractKeys(content);
        referenceKeys.set(namespace, keys);
      }
    }

    // 检查其他语言的键一致性
    for (const lang of SUPPORTED_LANGUAGES) {
      if (lang === 'en') continue;

      for (const namespace of REQUIRED_NAMESPACES) {
        const filePath = path.join(LOCALES_DIR, lang, `${namespace}.json`);
        if (!fs.existsSync(filePath)) continue;

        const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        const keys = this.extractKeys(content);
        const referenceKeySet = referenceKeys.get(namespace) || new Set();

        // 检查缺失的键
        for (const refKey of referenceKeySet) {
          if (!keys.has(refKey)) {
            this.errors.push(
              `Missing key "${refKey}" in ${lang}/${namespace}.json`
            );
          }
        }

        // 检查多余的键
        for (const key of keys) {
          if (!referenceKeySet.has(key)) {
            this.warnings.push(
              `Extra key "${key}" in ${lang}/${namespace}.json`
            );
          }
        }
      }
    }
  }

  extractKeys(obj, prefix = '') {
    const keys = new Set();

    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;

      if (typeof value === 'object' && value !== null) {
        const nestedKeys = this.extractKeys(value, fullKey);
        nestedKeys.forEach(k => keys.add(k));
      } else {
        keys.add(fullKey);
      }
    }

    return keys;
  }

  async validatePlurals() {
    const pluralSuffixes = ['zero', 'one', 'two', 'few', 'many', 'other'];

    for (const lang of SUPPORTED_LANGUAGES) {
      for (const namespace of REQUIRED_NAMESPACES) {
        const filePath = path.join(LOCALES_DIR, lang, `${namespace}.json`);
        if (!fs.existsSync(filePath)) continue;

        const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        await this.validatePluralKeys(content, `${lang}/${namespace}.json`);
      }
    }
  }

  async validatePluralKeys(obj, filePath, keyPath = '') {
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = keyPath ? `${keyPath}.${key}` : key;

      if (typeof value === 'object' && value !== null) {
        await this.validatePluralKeys(value, filePath, fullKey);
      } else if (key.includes('_')) {
        const [baseKey, suffix] = key.split('_');
        const pluralSuffixes = ['zero', 'one', 'two', 'few', 'many', 'other'];

        if (pluralSuffixes.includes(suffix)) {
          // 验证复数形式键
          if (typeof value !== 'string') {
            this.errors.push(
              `Plural key "${fullKey}" should have string value in ${filePath}`
            );
          }
        }
      }
    }
  }

  reportResults() {
    console.log('\n📊 I18n Validation Results:');

    if (this.errors.length === 0 && this.warnings.length === 0) {
      console.log('✅ All internationalization files are valid!');
      return;
    }

    if (this.errors.length > 0) {
      console.log(`\n❌ ${this.errors.length} Error(s):`);
      this.errors.forEach(error => console.log(`   • ${error}`));
    }

    if (this.warnings.length > 0) {
      console.log(`\n⚠️  ${this.warnings.length} Warning(s):`);
      this.warnings.forEach(warning => console.log(`   • ${warning}`));
    }
  }
}

const validator = new I18nValidator();
validator.validate().catch(console.error);
```

**Package.json脚本**：

```json
{
  "scripts": {
    "i18n:validate": "node scripts/verify_i18n.mjs",
    "i18n:extract": "i18next-scanner --config i18next-scanner.config.js",
    "i18n:sync": "node scripts/sync_translations.mjs",
    "test:i18n": "vitest run tests/unit/i18n/",
    "test:i18n:e2e": "playwright test tests/e2e/i18n.electron.spec.ts",
    "guard:i18n": "npm run i18n:validate && npm run test:i18n && npm run test:i18n:e2e"
  }
}
```

### Positive Consequences

- 支持多语言动态切换，提升全球用户体验
- 命名空间和懒加载减少应用启动时间和内存占用
- 与Electron深度集成，主进程和渲染进程语言同步
- 支持复杂复数形式和文化敏感格式化
- 完整的测试覆盖确保国际化功能稳定性
- 自动化验证脚本确保翻译质量和一致性
- RTL语言支持覆盖更多国际市场

### Negative Consequences

- 增加构建包大小（多语言文件）
- 复杂语言切换逻辑增加维护成本
- 翻译内容管理需要额外流程和工具
- 某些第三方库可能不支持国际化
- RTL语言需要额外的CSS和布局调整
- 复数形式处理增加开发复杂度

## Verification

- **核心验证**: tests/unit/i18n/i18n.spec.ts, tests/e2e/i18n.electron.spec.ts
- **验证脚本**: scripts/verify_i18n.mjs
- **监控指标**: i18n.language_switch_success_rate, i18n.translation_load_time, i18n.missing_keys_count
- **质量门禁**: 100%翻译键覆盖率，语言切换E2E测试100%通过率

### 国际化验证矩阵

| 验证类型       | 工具       | 要求标准                       | 失败后果   |
| -------------- | ---------- | ------------------------------ | ---------- |
| **翻译完整性** | 自定义脚本 | 100%键覆盖率                   | CI自动阻断 |
| **语言切换**   | E2E测试    | 100%测试通过                   | PR自动阻断 |
| **格式化**     | 单元测试   | 日期/数字/货币格式正确         | CI自动阻断 |
| **复数形式**   | 单元测试   | 复数规则正确应用               | CI自动阻断 |
| **RTL支持**    | E2E测试    | HTML dir属性正确 + CSS样式验证 | PR自动阻断 |
| **性能**       | 性能测试   | 语言包加载<500ms               | 监控告警   |

## Operational Playbook

### 升级步骤

1. **依赖安装**: 安装react-i18next、i18next相关包和类型定义
2. **配置部署**: 创建i18n配置文件和hook封装
3. **语言包创建**: 建立语言包目录结构和初始翻译文件
4. **组件集成**: 在React组件中集成useI18n hook
5. **Electron集成**: 配置主进程语言同步和菜单本地化
6. **测试部署**: 建立单元测试和E2E测试套件

### 回滚步骤

1. **应急降级**: 快速切换回硬编码英语文本（通过环境变量）
2. **语言包恢复**: 从备份恢复损坏的语言包文件
3. **配置回滚**: 恢复到单语言配置并禁用语言切换功能
4. **测试验证**: 确保回滚后应用功能正常
5. **问题分析**: 分析国际化问题原因并制定修复计划

### 维护指南

- **翻译更新**: 建立翻译审核流程，确保文案质量和一致性
- **性能监控**: 监控语言包加载时间和语言切换响应时间
- **键值管理**: 定期清理无用翻译键，避免冗余
- **质量保证**: 每次发布前运行完整的i18n验证套件
- **用户反馈**: 建立多语言用户反馈收集和处理机制

## References

- **CH章节关联**: CH01, CH04, CH10
- **相关ADR**: ADR-0001-tech-stack, ADR-0005-quality-gates
- **外部文档**:
  - [react-i18next Documentation](https://react.i18next.com/)
  - [i18next Configuration](https://www.i18next.com/overview/configuration-options)
  - [Unicode Locale Data Markup Language](https://unicode.org/reports/tr35/)
  - [Electron Localization](https://www.electronjs.org/docs/latest/tutorial/localization)
- **国际化标准**: BCP 47 Language Tags, Unicode CLDR, ISO 639 Language Codes
- **相关PRD-ID**: 适用于所有需要多语言支持的PRD功能模块
