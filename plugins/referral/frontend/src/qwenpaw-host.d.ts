// Ambient declarations for the QwenPaw console host API.
//
// The QwenPaw console injects a shared `window.QwenPaw` object at
// runtime; we externalize `react`/`react-dom` (see `vite.config.ts`)
// and pull `React`/`antd` off `host` instead of bundling them. Without
// these declarations every access reduces to `any` and the compiler
// cannot tell us when the host contract drifts (e.g. `host.antd` being
// renamed or replaced).

import type * as ReactNS from "react";

declare global {
  interface QwenPawHost {
    /** React module re-exported by the host (same major version as antd). */
    React: typeof ReactNS;
    /**
     * antd module re-exported by the host. Typed loosely on purpose:
     * antd's public types are huge and the plugin only uses a handful
     * of named exports through destructuring, so a structural `any`
     * shape here keeps the surface small while still letting `Pick`-
     * style destructuring compile.
     */
    antd: any;
    /** @ant-design/icons module (component references for sidebar icons). */
    antdIcons: any;
    /** Resolve a console-relative API path to an absolute URL. */
    getApiUrl: (path: string) => string;
    /** Current bearer token for QwenPaw API calls (may be empty). */
    getApiToken: () => string;
  }

  /** Legacy route declaration (used by registerRoutes). */
  interface QwenPawRoute {
    path: string;
    component: unknown;
    label?: string;
    icon?: string;
    priority?: number;
  }

  /** Menu item shape for the new Menu API (QwenPaw.menu.add). */
  interface QwenPawMenuItem {
    id: string;
    location?: "primary.agentScoped" | "primary.settings" | "userMenu";
    parentId?: string;
    before?: string;
    after?: string;
    order?: number;
    label: string;
    icon?: unknown;
    route?: string;
    href?: string;
    visible?: () => boolean;
    isGroup?: boolean;
    divider?: boolean;
  }

  /** Route entry shape for the new Route API (QwenPaw.route.add). */
  interface QwenPawRouteItem {
    id: string;
    path: string;
    component: unknown;
  }

  /** Disposable handle returned by menu.add / route.add. */
  interface QwenPawDisposable {
    dispose(): void;
  }

  /** Plugin-facing Route namespace (QwenPaw.route). */
  interface QwenPawRouteNamespace {
    add(pluginId: string, route: QwenPawRouteItem | QwenPawRouteItem[]): QwenPawDisposable;
    replace(pluginId: string, targetId: string, component: unknown): QwenPawDisposable;
    wrap(pluginId: string, targetId: string, wrapper: (Inner: unknown) => unknown): QwenPawDisposable;
    remove(targetId: string): void;
  }

  /** Plugin-facing Menu namespace (QwenPaw.menu). */
  interface QwenPawMenuNamespace {
    add(pluginId: string, item: QwenPawMenuItem | QwenPawMenuItem[]): QwenPawDisposable;
    replace(pluginId: string, targetId: string, item: QwenPawMenuItem): QwenPawDisposable;
    remove(targetId: string): void;
  }

  interface QwenPawGlobal {
    host: QwenPawHost;
    /** Legacy route registration (translates to menu+route internally). */
    registerRoutes?: (pluginId: string, routes: QwenPawRoute[]) => void;
    /** New Menu API — add/remove sidebar entries with full placement control. */
    menu?: QwenPawMenuNamespace;
    /** New Route API — register page routes independently from menu. */
    route?: QwenPawRouteNamespace;
  }

  interface Window {
    QwenPaw: QwenPawGlobal;
  }
}

export {};
