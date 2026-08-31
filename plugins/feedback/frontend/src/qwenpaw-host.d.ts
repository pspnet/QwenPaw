import type * as ReactNS from "react";

declare global {
  interface QwenPawHost {
    React: typeof ReactNS;
    antd: any;
    antdIcons: any;
    getApiUrl: (path: string) => string;
    getApiToken: () => string;
  }

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

  interface QwenPawRouteItem {
    id: string;
    path: string;
    component: unknown;
  }

  interface QwenPawDisposable {
    dispose(): void;
  }

  interface QwenPawRouteNamespace {
    add(pluginId: string, route: QwenPawRouteItem | QwenPawRouteItem[]): QwenPawDisposable;
    replace(pluginId: string, targetId: string, component: unknown): QwenPawDisposable;
    wrap(pluginId: string, targetId: string, wrapper: (Inner: unknown) => unknown): QwenPawDisposable;
    remove(targetId: string): void;
  }

  interface QwenPawMenuNamespace {
    add(pluginId: string, item: QwenPawMenuItem | QwenPawMenuItem[]): QwenPawDisposable;
    replace(pluginId: string, targetId: string, item: QwenPawMenuItem): QwenPawDisposable;
    remove(targetId: string): void;
  }

  interface QwenPawGlobal {
    host: QwenPawHost;
    registerRoutes?: (pluginId: string, routes: any[]) => void;
    menu?: QwenPawMenuNamespace;
    route?: QwenPawRouteNamespace;
  }

  interface Window {
    QwenPaw: QwenPawGlobal;
  }
}

export {};
