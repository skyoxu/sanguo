---
ADR-ID: ADR-0009
title: 跨平台兼容策略 - Windows/macOS/Linux统一
status: Superseded
decision-time: '2025-08-17'
deciders: [架构团队, 开发团队, UX团队]
archRefs: [CH04, CH09, CH11]
verification:
  - path: tests/e2e/os-matrix.spec.ts
    assert: Platform behaviors (paths, menus, tray, shortcuts) pass on Win/macOS/Linux
  - path: scripts/os/feature-probes.mjs
    assert: Platform feature probes (notifications, proxies, SAB) report expected capabilities
  - path: scripts/perf/os-baselines.json
    assert: Per-OS performance baselines are within drift threshold
impact-scope:
  - electron/
  - scripts/platform/
  - tests/e2e/platform/
tech-tags:
  - cross-platform
  - windows
  - macos
  - linux
  - compatibility
depends-on: []
depended-by: []
test-coverage: tests/unit/adr-0009.spec.ts
monitoring-metrics:
  - implementation_coverage
  - compliance_rate
executable-deliverables:
  - scripts/platform-detection.mjs
  - electron/platform-specific.ts
  - tests/e2e/platform/cross-platform.spec.ts
supersedes: []
superseded-by: [ADR-0011]
---

# ADR-0009: 跨平台适配策略（已被 Windows-only 平台策略替代）

## Context and Problem Statement

Electron游戏应用需要在Windows、macOS、Linux三大平台上提供一致的用户体验，同时充分利用各平台的原生特性。需要处理平台间的差异，包括UI设计规范、文件系统、快捷键、系统集成、性能优化等方面，确保应用在各平台上都能正常运行并符合用户预期。

## Decision Drivers

- 需要在三大主流平台（Windows、macOS、Linux）上提供一致的功能
- 需要遵循各平台的UI/UX设计规范和用户习惯
- 需要处理平台特定的文件路径、权限、系统调用
- 需要优化各平台的性能表现和资源使用
- 需要支持平台特定的系统集成功能
- 需要简化跨平台开发和维护成本
- 需要确保应用在所有平台上的稳定性

## Considered Options

- **统一适配器模式 + 平台检测** (选择方案)
- **平台独立构建分支**
- **仅支持主流平台（Windows+macOS）**
- **Web应用替代（功能受限）**
- **原生应用分别开发（成本过高）**

## Decision Outcome

选择的方案：**统一适配器模式 + 平台检测**

### 平台检测与抽象层

**平台检测服务**：

```typescript
// src/shared/platform/platform-detector.ts
export enum Platform {
  WINDOWS = 'windows',
  MACOS = 'darwin',
  LINUX = 'linux',
}

export interface PlatformInfo {
  platform: Platform;
  version: string;
  arch: string;
  isARM: boolean;
  isX64: boolean;
  homeDir: string;
  tempDir: string;
  executableName: string;
}

export class PlatformDetector {
  private static _instance: PlatformDetector;
  private _platformInfo: PlatformInfo;

  private constructor() {
    this._platformInfo = this.detectPlatform();
  }

  public static getInstance(): PlatformDetector {
    if (!PlatformDetector._instance) {
      PlatformDetector._instance = new PlatformDetector();
    }
    return PlatformDetector._instance;
  }

  public getPlatformInfo(): PlatformInfo {
    return this._platformInfo;
  }

  public isWindows(): boolean {
    return this._platformInfo.platform === Platform.WINDOWS;
  }

  public isMacOS(): boolean {
    return this._platformInfo.platform === Platform.MACOS;
  }

  public isLinux(): boolean {
    return this._platformInfo.platform === Platform.LINUX;
  }

  private detectPlatform(): PlatformInfo {
    const os = require('os');

    return {
      platform: os.platform() as Platform,
      version: os.release(),
      arch: os.arch(),
      isARM: os.arch().includes('arm'),
      isX64: os.arch() === 'x64',
      homeDir: os.homedir(),
      tempDir: os.tmpdir(),
      executableName: this.getExecutableName(os.platform()),
    };
  }

  private getExecutableName(platform: string): string {
    switch (platform) {
      case 'win32':
        return 'BuildGame.exe';
      case 'darwin':
        return 'BuildGame.app';
      case 'linux':
        return 'buildgame';
      default:
        return 'buildgame';
    }
  }
}
```

### 平台特定适配器

**文件系统适配器**：

```typescript
// src/shared/platform/adapters/file-system.adapter.ts
export abstract class FileSystemAdapter {
  abstract getConfigPath(): string;
  abstract getDataPath(): string;
  abstract getLogPath(): string;
  abstract getCachePath(): string;
  abstract getDownloadPath(): string;
  abstract openFileExplorer(path: string): Promise<void>;
  abstract openTerminal(path?: string): Promise<void>;
  abstract getShortcutPath(): string;
}

export class WindowsFileSystemAdapter extends FileSystemAdapter {
  getConfigPath(): string {
    return path.join(os.homedir(), 'AppData', 'Roaming', 'BuildGame');
  }

  getDataPath(): string {
    return path.join(os.homedir(), 'AppData', 'Local', 'BuildGame');
  }

  getLogPath(): string {
    return path.join(this.getDataPath(), 'logs');
  }

  getCachePath(): string {
    return path.join(this.getDataPath(), 'cache');
  }

  getDownloadPath(): string {
    return path.join(os.homedir(), 'Downloads');
  }

  async openFileExplorer(filePath: string): Promise<void> {
    const { shell } = require('electron');
    await shell.openPath(filePath);
  }

  async openTerminal(workingDir?: string): Promise<void> {
    const { spawn } = require('child_process');
    const cwd = workingDir || this.getDataPath();
    spawn('cmd', ['/c', 'start', 'cmd'], { cwd, detached: true });
  }

  getShortcutPath(): string {
    return path.join(os.homedir(), 'Desktop', 'BuildGame.lnk');
  }
}

export class MacOSFileSystemAdapter extends FileSystemAdapter {
  getConfigPath(): string {
    return path.join(
      os.homedir(),
      'Library',
      'Application Support',
      'BuildGame'
    );
  }

  getDataPath(): string {
    return path.join(
      os.homedir(),
      'Library',
      'Application Support',
      'BuildGame'
    );
  }

  getLogPath(): string {
    return path.join(os.homedir(), 'Library', 'Logs', 'BuildGame');
  }

  getCachePath(): string {
    return path.join(os.homedir(), 'Library', 'Caches', 'BuildGame');
  }

  getDownloadPath(): string {
    return path.join(os.homedir(), 'Downloads');
  }

  async openFileExplorer(filePath: string): Promise<void> {
    const { shell } = require('electron');
    await shell.showItemInFolder(filePath);
  }

  async openTerminal(workingDir?: string): Promise<void> {
    const { spawn } = require('child_process');
    const cwd = workingDir || this.getDataPath();
    spawn('open', ['-a', 'Terminal', cwd], { detached: true });
  }

  getShortcutPath(): string {
    return path.join(os.homedir(), 'Desktop', 'BuildGame.app');
  }
}

export class LinuxFileSystemAdapter extends FileSystemAdapter {
  getConfigPath(): string {
    const xdgConfig = process.env.XDG_CONFIG_HOME;
    return xdgConfig
      ? path.join(xdgConfig, 'buildgame')
      : path.join(os.homedir(), '.config', 'buildgame');
  }

  getDataPath(): string {
    const xdgData = process.env.XDG_DATA_HOME;
    return xdgData
      ? path.join(xdgData, 'buildgame')
      : path.join(os.homedir(), '.local', 'share', 'buildgame');
  }

  getLogPath(): string {
    return path.join(this.getDataPath(), 'logs');
  }

  getCachePath(): string {
    const xdgCache = process.env.XDG_CACHE_HOME;
    return xdgCache
      ? path.join(xdgCache, 'buildgame')
      : path.join(os.homedir(), '.cache', 'buildgame');
  }

  getDownloadPath(): string {
    const xdgDownload = process.env.XDG_DOWNLOAD_DIR;
    return xdgDownload || path.join(os.homedir(), 'Downloads');
  }

  async openFileExplorer(filePath: string): Promise<void> {
    const { spawn } = require('child_process');
    // 尝试多种文件管理器
    const fileManagers = [
      'nautilus',
      'dolphin',
      'thunar',
      'pcmanfm',
      'xdg-open',
    ];

    for (const manager of fileManagers) {
      try {
        spawn(manager, [filePath], { detached: true, stdio: 'ignore' });
        return;
      } catch (error) {
        continue; // 尝试下一个
      }
    }
  }

  async openTerminal(workingDir?: string): Promise<void> {
    const { spawn } = require('child_process');
    const cwd = workingDir || this.getDataPath();

    // 尝试多种终端模拟器
    const terminals = [
      ['gnome-terminal', '--working-directory=' + cwd],
      ['konsole', '--workdir', cwd],
      ['xfce4-terminal', '--default-working-directory=' + cwd],
      ['xterm', '-e', 'cd ' + cwd + ' && bash'],
    ];

    for (const [terminal, ...args] of terminals) {
      try {
        spawn(terminal, args, { detached: true, stdio: 'ignore' });
        return;
      } catch (error) {
        continue;
      }
    }
  }

  getShortcutPath(): string {
    return path.join(os.homedir(), 'Desktop', 'buildgame.desktop');
  }
}
```

### 快捷键适配

**快捷键适配器**：

```typescript
// src/shared/platform/adapters/keyboard.adapter.ts
export interface KeyboardShortcut {
  key: string;
  modifiers: string[];
  description: string;
}

export abstract class KeyboardAdapter {
  abstract getShortcuts(): Map<string, KeyboardShortcut>;
  abstract getModifierKey(): string; // Ctrl/Cmd
  abstract getMenuAccelerator(shortcut: string): string;
}

export class WindowsKeyboardAdapter extends KeyboardAdapter {
  getShortcuts(): Map<string, KeyboardShortcut> {
    return new Map([
      ['new-game', { key: 'N', modifiers: ['Ctrl'], description: '新游戏' }],
      ['save-game', { key: 'S', modifiers: ['Ctrl'], description: '保存游戏' }],
      [
        'open-settings',
        { key: ',', modifiers: ['Ctrl'], description: '打开设置' },
      ],
      [
        'toggle-fullscreen',
        { key: 'F11', modifiers: [], description: '全屏切换' },
      ],
      ['quit-app', { key: 'F4', modifiers: ['Alt'], description: '退出应用' }],
      ['minimize', { key: 'M', modifiers: ['Ctrl'], description: '最小化' }],
      ['copy', { key: 'C', modifiers: ['Ctrl'], description: '复制' }],
      ['paste', { key: 'V', modifiers: ['Ctrl'], description: '粘贴' }],
    ]);
  }

  getModifierKey(): string {
    return 'Ctrl';
  }

  getMenuAccelerator(shortcut: string): string {
    const mapping: Record<string, string> = {
      'new-game': 'Ctrl+N',
      'save-game': 'Ctrl+S',
      'open-settings': 'Ctrl+,',
      'toggle-fullscreen': 'F11',
      'quit-app': 'Alt+F4',
    };
    return mapping[shortcut] || '';
  }
}

export class MacOSKeyboardAdapter extends KeyboardAdapter {
  getShortcuts(): Map<string, KeyboardShortcut> {
    return new Map([
      ['new-game', { key: 'N', modifiers: ['Cmd'], description: '新游戏' }],
      ['save-game', { key: 'S', modifiers: ['Cmd'], description: '保存游戏' }],
      [
        'open-settings',
        { key: ',', modifiers: ['Cmd'], description: '打开设置' },
      ],
      [
        'toggle-fullscreen',
        { key: 'F', modifiers: ['Cmd', 'Ctrl'], description: '全屏切换' },
      ],
      ['quit-app', { key: 'Q', modifiers: ['Cmd'], description: '退出应用' }],
      ['minimize', { key: 'M', modifiers: ['Cmd'], description: '最小化' }],
      ['hide', { key: 'H', modifiers: ['Cmd'], description: '隐藏窗口' }],
      ['copy', { key: 'C', modifiers: ['Cmd'], description: '复制' }],
      ['paste', { key: 'V', modifiers: ['Cmd'], description: '粘贴' }],
    ]);
  }

  getModifierKey(): string {
    return 'Cmd';
  }

  getMenuAccelerator(shortcut: string): string {
    const mapping: Record<string, string> = {
      'new-game': 'CmdOrCtrl+N',
      'save-game': 'CmdOrCtrl+S',
      'open-settings': 'CmdOrCtrl+,',
      'toggle-fullscreen': 'Cmd+Ctrl+F',
      'quit-app': 'CmdOrCtrl+Q',
      minimize: 'CmdOrCtrl+M',
      hide: 'Cmd+H',
    };
    return mapping[shortcut] || '';
  }
}
```

### UI主题适配

**主题适配器**：

```typescript
// src/shared/platform/adapters/theme.adapter.ts
export interface PlatformTheme {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    surface: string;
    text: string;
    border: string;
  };
  typography: {
    fontFamily: string;
    fontSize: {
      small: string;
      medium: string;
      large: string;
    };
  };
  spacing: {
    small: string;
    medium: string;
    large: string;
  };
  borderRadius: string;
  shadows: {
    light: string;
    medium: string;
    heavy: string;
  };
}

export abstract class ThemeAdapter {
  abstract getTheme(): PlatformTheme;
  abstract isDarkMode(): boolean;
  abstract getSystemTheme(): 'light' | 'dark' | 'system';
}

export class WindowsThemeAdapter extends ThemeAdapter {
  getTheme(): PlatformTheme {
    return {
      colors: {
        primary: '#0078d4',
        secondary: '#6b6b6b',
        accent: '#005a9e',
        background: '#ffffff',
        surface: '#f5f5f5',
        text: '#323130',
        border: '#d1d1d1',
      },
      typography: {
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        fontSize: {
          small: '12px',
          medium: '14px',
          large: '16px',
        },
      },
      spacing: {
        small: '4px',
        medium: '8px',
        large: '16px',
      },
      borderRadius: '2px',
      shadows: {
        light: '0 1px 3px rgba(0,0,0,0.12)',
        medium: '0 4px 6px rgba(0,0,0,0.15)',
        heavy: '0 8px 20px rgba(0,0,0,0.20)',
      },
    };
  }

  isDarkMode(): boolean {
    // Windows系统主题检测
    const { systemPreferences } = require('electron');
    return systemPreferences.shouldUseDarkColors();
  }

  getSystemTheme(): 'light' | 'dark' | 'system' {
    return this.isDarkMode() ? 'dark' : 'light';
  }
}

export class MacOSThemeAdapter extends ThemeAdapter {
  getTheme(): PlatformTheme {
    return {
      colors: {
        primary: '#007aff',
        secondary: '#8e8e93',
        accent: '#5856d6',
        background: '#ffffff',
        surface: '#f2f2f7',
        text: '#000000',
        border: '#c6c6c8',
      },
      typography: {
        fontFamily: '-apple-system, BlinkMacSystemFont, system-ui, sans-serif',
        fontSize: {
          small: '11px',
          medium: '13px',
          large: '15px',
        },
      },
      spacing: {
        small: '6px',
        medium: '12px',
        large: '20px',
      },
      borderRadius: '8px',
      shadows: {
        light: '0 1px 3px rgba(0,0,0,0.10)',
        medium: '0 4px 14px rgba(0,0,0,0.12)',
        heavy: '0 25px 55px rgba(0,0,0,0.21)',
      },
    };
  }

  isDarkMode(): boolean {
    const { systemPreferences } = require('electron');
    return systemPreferences.isDarkMode();
  }

  getSystemTheme(): 'light' | 'dark' | 'system' {
    return this.isDarkMode() ? 'dark' : 'light';
  }
}

export class LinuxThemeAdapter extends ThemeAdapter {
  getTheme(): PlatformTheme {
    return {
      colors: {
        primary: '#3584e4',
        secondary: '#77767b',
        accent: '#9141ac',
        background: '#ffffff',
        surface: '#fafafa',
        text: '#2e3436',
        border: '#c0bfbc',
      },
      typography: {
        fontFamily: 'Ubuntu, "Noto Sans", system-ui, sans-serif',
        fontSize: {
          small: '10px',
          medium: '12px',
          large: '14px',
        },
      },
      spacing: {
        small: '4px',
        medium: '8px',
        large: '16px',
      },
      borderRadius: '4px',
      shadows: {
        light: '0 1px 3px rgba(0,0,0,0.16)',
        medium: '0 3px 6px rgba(0,0,0,0.20)',
        heavy: '0 10px 20px rgba(0,0,0,0.25)',
      },
    };
  }

  isDarkMode(): boolean {
    // 检查GTK主题或环境变量
    const gtkTheme = process.env.GTK_THEME;
    return gtkTheme?.toLowerCase().includes('dark') || false;
  }

  getSystemTheme(): 'light' | 'dark' | 'system' {
    return this.isDarkMode() ? 'dark' : 'light';
  }
}
```

### 窗口管理适配

**窗口适配器**：

```typescript
// src/shared/platform/adapters/window.adapter.ts
export interface WindowConfig {
  minWidth: number;
  minHeight: number;
  defaultWidth: number;
  defaultHeight: number;
  titleBarStyle: 'default' | 'hidden' | 'hiddenInset';
  vibrancy?: string;
  transparent: boolean;
  frame: boolean;
  show: boolean;
}

export abstract class WindowAdapter {
  abstract getWindowConfig(): WindowConfig;
  abstract setupWindow(window: BrowserWindow): void;
  abstract handleWindowEvents(window: BrowserWindow): void;
}

export class WindowsWindowAdapter extends WindowAdapter {
  getWindowConfig(): WindowConfig {
    return {
      minWidth: 800,
      minHeight: 600,
      defaultWidth: 1200,
      defaultHeight: 800,
      titleBarStyle: 'default',
      transparent: false,
      frame: true,
      show: true,
    };
  }

  setupWindow(window: BrowserWindow): void {
    // Windows特定的窗口设置
    window.setMenuBarVisibility(false);

    // Windows 11特效支持
    if (
      process.platform === 'win32' &&
      process.getSystemVersion() >= '10.0.22000'
    ) {
      window.setBackgroundMaterial('acrylic');
    }
  }

  handleWindowEvents(window: BrowserWindow): void {
    window.on('minimize', () => {
      // Windows最小化行为
      window.hide();
    });

    window.on('close', event => {
      // 阻止默认关闭，最小化到系统托盘
      event.preventDefault();
      window.hide();
    });
  }
}

export class MacOSWindowAdapter extends WindowAdapter {
  getWindowConfig(): WindowConfig {
    return {
      minWidth: 800,
      minHeight: 600,
      defaultWidth: 1200,
      defaultHeight: 800,
      titleBarStyle: 'hiddenInset',
      vibrancy: 'window',
      transparent: true,
      frame: true,
      show: true,
    };
  }

  setupWindow(window: BrowserWindow): void {
    // macOS特定的窗口设置
    window.setWindowButtonVisibility(true);

    // 设置窗口级别
    window.setAlwaysOnTop(false);

    // macOS原生全屏支持
    window.setFullScreenable(true);
  }

  handleWindowEvents(window: BrowserWindow): void {
    window.on('close', event => {
      // macOS标准行为：隐藏窗口而不是退出应用
      if (!app.isQuittingAll) {
        event.preventDefault();
        window.hide();
      }
    });

    window.on('minimize', () => {
      // macOS最小化到Dock
      window.minimize();
    });
  }
}

export class LinuxWindowAdapter extends WindowAdapter {
  getWindowConfig(): WindowConfig {
    return {
      minWidth: 800,
      minHeight: 600,
      defaultWidth: 1200,
      defaultHeight: 800,
      titleBarStyle: 'default',
      transparent: false,
      frame: true,
      show: true,
    };
  }

  setupWindow(window: BrowserWindow): void {
    // Linux特定的窗口设置
    window.setIcon(path.join(__dirname, '../assets/icon.png'));

    // Wayland支持
    if (process.env.WAYLAND_DISPLAY) {
      window.setBackgroundColor('#ffffff');
    }
  }

  handleWindowEvents(window: BrowserWindow): void {
    window.on('close', () => {
      // Linux标准行为：直接关闭应用
      app.quit();
    });
  }
}
```

### 系统集成适配

**系统集成适配器**：

```typescript
// src/shared/platform/adapters/system-integration.adapter.ts
export abstract class SystemIntegrationAdapter {
  abstract setupAutoStart(enabled: boolean): Promise<void>;
  abstract createDesktopShortcut(): Promise<void>;
  abstract setupSystemTray(): Tray | null;
  abstract handleDeepLinks(protocol: string): void;
  abstract getSystemInfo(): SystemInfo;
}

export class WindowsSystemIntegrationAdapter extends SystemIntegrationAdapter {
  async setupAutoStart(enabled: boolean): Promise<void> {
    const { app } = require('electron');

    app.setLoginItemSettings({
      openAtLogin: enabled,
      openAsHidden: true,
      path: app.getPath('exe'),
      args: ['--hidden'],
    });
  }

  async createDesktopShortcut(): Promise<void> {
    const { shell, app } = require('electron');
    const shortcutPath = path.join(os.homedir(), 'Desktop', 'BuildGame.lnk');

    shell.writeShortcutLink(shortcutPath, 'create', {
      target: app.getPath('exe'),
      cwd: path.dirname(app.getPath('exe')),
      description: 'Build Game - 桌面游戏应用',
      icon: app.getPath('exe'),
      iconIndex: 0,
    });
  }

  setupSystemTray(): Tray | null {
    const { Tray, Menu, nativeImage } = require('electron');
    const iconPath = path.join(__dirname, '../assets/tray-icon.ico');
    const icon = nativeImage.createFromPath(iconPath);

    const tray = new Tray(icon);
    tray.setToolTip('Build Game');

    const contextMenu = Menu.buildFromTemplate([
      { label: '显示主窗口', click: () => this.showMainWindow() },
      { label: '新游戏', click: () => this.startNewGame() },
      { type: 'separator' },
      { label: '退出', click: () => app.quit() },
    ]);

    tray.setContextMenu(contextMenu);
    return tray;
  }

  handleDeepLinks(protocol: string): void {
    const { app } = require('electron');

    if (process.defaultApp) {
      if (process.argv.length >= 2) {
        app.setAsDefaultProtocolClient(protocol, process.execPath, [
          path.resolve(process.argv[1]),
        ]);
      }
    } else {
      app.setAsDefaultProtocolClient(protocol);
    }
  }

  getSystemInfo(): SystemInfo {
    const os = require('os');
    return {
      platform: 'Windows',
      version: os.release(),
      arch: os.arch(),
      totalMemory: os.totalmem(),
      freeMemory: os.freemem(),
      cpus: os.cpus().length,
      uptime: os.uptime(),
    };
  }

  private showMainWindow(): void {
    // 实现显示主窗口逻辑
  }

  private startNewGame(): void {
    // 实现新游戏逻辑
  }
}
```

### 平台适配工厂

**适配器工厂**：

```typescript
// src/shared/platform/platform-adapter.factory.ts
export class PlatformAdapterFactory {
  private static fileSystemAdapter: FileSystemAdapter;
  private static keyboardAdapter: KeyboardAdapter;
  private static themeAdapter: ThemeAdapter;
  private static windowAdapter: WindowAdapter;
  private static systemIntegrationAdapter: SystemIntegrationAdapter;

  public static getFileSystemAdapter(): FileSystemAdapter {
    if (!this.fileSystemAdapter) {
      const platform =
        PlatformDetector.getInstance().getPlatformInfo().platform;

      switch (platform) {
        case Platform.WINDOWS:
          this.fileSystemAdapter = new WindowsFileSystemAdapter();
          break;
        case Platform.MACOS:
          this.fileSystemAdapter = new MacOSFileSystemAdapter();
          break;
        case Platform.LINUX:
          this.fileSystemAdapter = new LinuxFileSystemAdapter();
          break;
      }
    }
    return this.fileSystemAdapter;
  }

  public static getKeyboardAdapter(): KeyboardAdapter {
    if (!this.keyboardAdapter) {
      const platform =
        PlatformDetector.getInstance().getPlatformInfo().platform;

      switch (platform) {
        case Platform.WINDOWS:
          this.keyboardAdapter = new WindowsKeyboardAdapter();
          break;
        case Platform.MACOS:
          this.keyboardAdapter = new MacOSKeyboardAdapter();
          break;
        case Platform.LINUX:
          this.keyboardAdapter = new WindowsKeyboardAdapter(); // Linux使用Windows样式
          break;
      }
    }
    return this.keyboardAdapter;
  }

  public static getThemeAdapter(): ThemeAdapter {
    if (!this.themeAdapter) {
      const platform =
        PlatformDetector.getInstance().getPlatformInfo().platform;

      switch (platform) {
        case Platform.WINDOWS:
          this.themeAdapter = new WindowsThemeAdapter();
          break;
        case Platform.MACOS:
          this.themeAdapter = new MacOSThemeAdapter();
          break;
        case Platform.LINUX:
          this.themeAdapter = new LinuxThemeAdapter();
          break;
      }
    }
    return this.themeAdapter;
  }

  public static getAllAdapters() {
    return {
      fileSystem: this.getFileSystemAdapter(),
      keyboard: this.getKeyboardAdapter(),
      theme: this.getThemeAdapter(),
      window: this.getWindowAdapter(),
      systemIntegration: this.getSystemIntegrationAdapter(),
    };
  }
}
```

### React跨平台UI组件

**平台感知UI组件**：

```tsx
// src/components/platform/PlatformButton.tsx
import React from 'react';
import { PlatformAdapterFactory } from '../../shared/platform/platform-adapter.factory';

interface PlatformButtonProps {
  children: React.ReactNode;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  className?: string;
}

export const PlatformButton: React.FC<PlatformButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  className = '',
}) => {
  const themeAdapter = PlatformAdapterFactory.getThemeAdapter();
  const theme = themeAdapter.getTheme();

  const baseStyles = {
    fontFamily: theme.typography.fontFamily,
    fontSize: theme.typography.fontSize.medium,
    padding: `${theme.spacing.medium} ${theme.spacing.large}`,
    borderRadius: theme.borderRadius,
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  };

  const variantStyles = {
    primary: {
      backgroundColor: theme.colors.primary,
      color: '#ffffff',
      boxShadow: theme.shadows.medium,
    },
    secondary: {
      backgroundColor: theme.colors.surface,
      color: theme.colors.text,
      border: `1px solid ${theme.colors.border}`,
      boxShadow: theme.shadows.light,
    },
  };

  return (
    <button
      className={className}
      style={{ ...baseStyles, ...variantStyles[variant] }}
      onClick={onClick}
      onMouseOver={e => {
        e.currentTarget.style.opacity = '0.9';
      }}
      onMouseOut={e => {
        e.currentTarget.style.opacity = '1';
      }}
    >
      {children}
    </button>
  );
};
```

### 性能优化配置

**平台性能优化**：

```typescript
// src/shared/platform/performance-optimizer.ts
export class PlatformPerformanceOptimizer {
  public static optimizeForPlatform(): void {
    const platform = PlatformDetector.getInstance().getPlatformInfo().platform;

    switch (platform) {
      case Platform.WINDOWS:
        this.optimizeForWindows();
        break;
      case Platform.MACOS:
        this.optimizeForMacOS();
        break;
      case Platform.LINUX:
        this.optimizeForLinux();
        break;
    }
  }

  private static optimizeForWindows(): void {
    // Windows特定优化
    const { app } = require('electron');

    // 启用Windows硬件加速
    app.commandLine.appendSwitch('enable-gpu-rasterization');
    app.commandLine.appendSwitch('enable-zero-copy');

    // Windows DPI适配
    app.commandLine.appendSwitch('high-dpi-support', '1');
    app.commandLine.appendSwitch('force-device-scale-factor', '1');
  }

  private static optimizeForMacOS(): void {
    // macOS特定优化
    const { app } = require('electron');

    // 启用macOS原生渲染
    app.commandLine.appendSwitch('enable-quartz-compositor');

    // Retina支持
    app.commandLine.appendSwitch('force-device-scale-factor', '2');

    // 金属渲染支持
    app.commandLine.appendSwitch('enable-metal');
  }

  private static optimizeForLinux(): void {
    // Linux特定优化
    const { app } = require('electron');

    // 启用GPU加速
    app.commandLine.appendSwitch('enable-gpu');
    app.commandLine.appendSwitch('ignore-gpu-blacklist');

    // Wayland支持
    if (process.env.WAYLAND_DISPLAY) {
      app.commandLine.appendSwitch('enable-features', 'UseOzonePlatform');
      app.commandLine.appendSwitch('ozone-platform', 'wayland');
    }
  }
}
```

### Positive Consequences

- 在所有主流平台上提供一致的功能和用户体验
- 充分利用各平台的原生特性和设计规范
- 统一的适配器模式简化了跨平台开发
- 自动的平台检测和适配减少手动配置
- 性能优化针对各平台特点进行调优
- 支持平台特定的系统集成功能
- 维护成本相对较低，代码复用率高

### Negative Consequences

- 适配器模式增加了代码复杂性
- 需要在多个平台上进行测试验证
- 平台特定功能可能存在兼容性问题
- Linux平台的碎片化增加适配难度
- 需要维护多套平台特定的资源文件
- 某些高级平台功能可能无法统一抽象

## Verification

- **测试验证**: tests/e2e/platform-compatibility.spec.ts, tests/unit/platform-adapters/\*.spec.ts
- **门禁脚本**: scripts/test_cross_platform.mjs, scripts/verify_platform_resources.mjs
- **监控指标**: platform.compatibility_score, ui.rendering_performance, system.integration_success
- **平台验证**: 多平台自动化测试、UI一致性验证、性能基准测试

### 跨平台验证清单

- [ ] 所有目标平台上的基本功能正常工作
- [ ] 平台特定的UI/UX符合各平台设计规范
- [ ] 文件路径和权限处理在所有平台正确
- [ ] 快捷键和菜单适配符合平台习惯
- [ ] 系统集成功能（托盘、自启动）正常
- [ ] 性能优化在各平台生效
- [ ] 安装包和更新在所有平台工作正常

## Operational Playbook

### 升级步骤

1. **平台检测**: 部署平台检测和适配器工厂系统
2. **适配器实现**: 为每个目标平台实现具体适配器
3. **UI组件**: 创建平台感知的UI组件库
4. **性能优化**: 实施平台特定的性能优化配置
5. **系统集成**: 集成平台特定的系统功能
6. **测试验证**: 在所有目标平台上进行完整测试

### 回滚步骤

1. **功能降级**: 如遇兼容性问题，可临时禁用特定平台功能
2. **适配器回退**: 回退到简化的适配器实现
3. **UI统一**: 临时使用统一的UI样式而非平台特定样式
4. **性能配置**: 恢复默认的性能配置
5. **问题隔离**: 隔离有问题的平台，确保其他平台正常工作

### 迁移指南

- **代码重构**: 现有代码需要适配平台检测和适配器模式
- **资源整理**: 整理和准备平台特定的资源文件
- **UI适配**: 调整UI组件以支持平台感知
- **测试环境**: 建立多平台测试环境和CI/CD流程
- **用户沟通**: 告知用户新的跨平台支持和改进

## References

- **CH章节关联**: CH09, CH01, CH10
- **相关ADR**: ADR-0001-tech-stack, ADR-0008-deployment-release, ADR-0002-electron-security
- **外部文档**:
  - [Electron Platform APIs](https://www.electronjs.org/docs/api/process)
  - [Windows Design Guidelines](https://docs.microsoft.com/en-us/windows/apps/design/)
  - [macOS Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/macos)
  - [GNOME Human Interface Guidelines](https://developer.gnome.org/hig/)
- **设计规范**: Windows Fluent Design, macOS Big Sur Design, Material Design for Linux
- **相关PRD-ID**: 适用于所有需要跨平台兼容的PRD模块
