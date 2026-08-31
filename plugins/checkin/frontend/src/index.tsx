// React and antd are injected by the QwenPaw console host at runtime;
// vite ``external``s them so nothing here is bundled. The type-only
// import below gives ``React.useState<T>()`` and friends real generic
// signatures (erased at build time, zero runtime cost).
//
// ``tsconfig.json`` sets ``"types": []`` so @types/* does not
// auto-register global namespaces. Without that, @types/react's
// ``export as namespace React`` would expose ``React`` as a global
// value and clash with the ``const React = host.React`` line below.
//
// ``qwenpaw-host.d.ts`` declares the ``window.QwenPaw`` contract so the
// compiler catches host-API drift instead of every access silently
// degrading to ``any``.
import type * as ReactNS from "react";

const host = window.QwenPaw.host;
const React: typeof ReactNS = host.React;
const antd = host.antd;
const getApiUrl = host.getApiUrl;
const getApiToken = host.getApiToken;
const antdIcons = host.antdIcons;

const {
  Card, Table, Button, Row, Col, Statistic,
  message, Tag, Typography,
} = antd;
// Renamed Typography.Text to AntText: ``Text`` collides with the
// global DOM ``Text`` interface from ``lib.dom.d.ts``.
const { Text: AntText } = Typography;

const { useState, useEffect, useCallback } = React;

const PLUGIN_ID = "checkin";

// ── Types ────────────────────────────────────────────────────────────

type CheckinRecord = {
  date: string;
  points_earned: number;
  consecutive_days: number;
  created_at: string;
};

type TodayResponse = {
  checked_in: boolean;
  record: CheckinRecord | null;
  date: string;
};

type CheckinResponse = {
  ok: boolean;
  already: boolean;
  record: CheckinRecord;
};

type HistoryResponse = {
  items: CheckinRecord[];
  total: number;
  page: number;
  size: number;
};

// ── Auth helpers (same pattern as qwenpaw-pet) ──────────────────────

function getSelectedAgentId(): string | null {
  try {
    const raw =
      window.sessionStorage?.getItem("qwenpaw-agent-storage") ??
      window.localStorage?.getItem("qwenpaw-agent-storage");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    const selected = parsed?.state?.selectedAgent;
    return typeof selected === "string" && selected ? selected : null;
  } catch {
    return null;
  }
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const t = getApiToken?.();
  if (t) headers.Authorization = `Bearer ${t}`;
  const agentId = getSelectedAgentId();
  if (agentId) headers["X-Agent-Id"] = agentId;
  return headers;
}

// ── API helpers ──────────────────────────────────────────────────────

async function apiGet(path: string): Promise<any> {
  const res = await fetch(getApiUrl(path), { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

async function apiPost(path: string): Promise<any> {
  const res = await fetch(getApiUrl(path), {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

// ── Page component ───────────────────────────────────────────────────

function CheckinPage() {
  const [todayChecked, setTodayChecked] = useState(false);
  const [todayRecord, setTodayRecord] = useState<CheckinRecord | null>(null);
  const [checking, setChecking] = useState(false);

  const [history, setHistory] = useState<CheckinRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  const [totalDays, setTotalDays] = useState(0);
  const [currentStreak, setCurrentStreak] = useState(0);

  // Check today's status
  useEffect(() => {
    apiGet("/checkin/today")
      .then((d: TodayResponse) => {
        setTodayChecked(d.checked_in);
        setTodayRecord(d.record);
      })
      .catch(() => {});
  }, []);

  // Load history
  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const d: HistoryResponse = await apiGet(
        `/checkin/history?page=${page}&size=${pageSize}`
      );
      const items = d.items || [];
      setHistory(items);
      setTotal(d.total || 0);
      if (page === 1 && items.length > 0) {
        setTotalDays(d.total || 0);
        setCurrentStreak(items[0].consecutive_days || 0);
      }
    } catch {
      // ignore
    }
    setLoading(false);
  }, [page, pageSize]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const handleCheckin = async () => {
    setChecking(true);
    try {
      const result: CheckinResponse = await apiPost("/checkin/today");
      if (result.already) {
        message.info("今日已签到");
      } else {
        const r = result.record;
        message.success(
          `签到成功！连续 ${r.consecutive_days} 天，获得 ${r.points_earned} 积分`,
        );
        setTodayChecked(true);
        setTodayRecord(r);
        setCurrentStreak(r.consecutive_days);
        setTotalDays(totalDays + 1);
        void loadHistory();
      }
    } catch (e: any) {
      message.error("签到失败: " + (e?.message || String(e)));
    } finally {
      setChecking(false);
    }
  };

  const formatDate = (v: string) => {
    if (!v) return "";
    return new Date(v).toLocaleDateString();
  };

  const formatDateTime = (v: string) => {
    if (!v) return "";
    const d = new Date(v);
    return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour12: false });
  };

  const columns = React.useMemo(
    () => [
      {
        title: "签到日期",
        dataIndex: "date",
        width: 140,
        render: formatDate,
      },
      {
        title: "获得积分",
        dataIndex: "points_earned",
        width: 120,
        render: (v: number) =>
          React.createElement(
            AntText,
            { style: { color: "#52c41a" } },
            `+${v}`,
          ),
      },
      {
        title: "连续天数",
        dataIndex: "consecutive_days",
        width: 120,
        render: (v: number) =>
          React.createElement(
            Tag,
            { color: v >= 7 ? "orange" : v >= 3 ? "blue" : "default" },
            `${v} 天`,
          ),
      },
      {
        title: "签到时间",
        dataIndex: "created_at",
        render: formatDateTime,
      },
    ],
    [],
  );

  return React.createElement(
    "div",
    { style: { padding: 24 } },
    React.createElement(
      "div",
      { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 } },
      React.createElement(
        AntText,
        { strong: true, style: { fontSize: 18 } },
        "签到",
      ),
      React.createElement(
        Button,
        {
          type: "primary",
          loading: checking,
          disabled: todayChecked,
          onClick: handleCheckin,
        },
        todayChecked ? "✓ 今日已签到" : "✋ 立即签到",
      ),
    ),
      // Stats row
      React.createElement(
        Row,
        { gutter: 24, style: { marginBottom: 24 } },
        React.createElement(
          Col,
          { span: 8 },
          React.createElement(
            Card,
            { size: "small", style: { textAlign: "center" as const } },
            React.createElement(Statistic, {
              title: "今日状态",
              value: todayChecked ? "已签到" : "未签到",
              valueStyle: {
                color: todayChecked ? "#52c41a" : "#faad14",
              },
            }),
          ),
        ),
        React.createElement(
          Col,
          { span: 8 },
          React.createElement(
            Card,
            { size: "small", style: { textAlign: "center" as const } },
            React.createElement(Statistic, {
              title: "连续签到",
              value: currentStreak,
              suffix: "天",
              valueStyle: {
                color: currentStreak >= 7 ? "#ff4d4f" : "#1890ff",
              },
            }),
          ),
        ),
        React.createElement(
          Col,
          { span: 8 },
          React.createElement(
            Card,
            { size: "small", style: { textAlign: "center" as const } },
            React.createElement(Statistic, {
              title: "累计签到",
              value: totalDays,
              suffix: "天",
            }),
          ),
        ),
      ),
      // Today's detail
      todayRecord
        ? React.createElement(
            Card,
            {
              size: "small",
              style: {
                marginBottom: 24,
                background: "#f6ffed",
                borderColor: "#b7eb8f",
              },
            },
            React.createElement(
              Row,
              { gutter: 16 },
              React.createElement(
                Col,
                { span: 8 },
                React.createElement(
                  AntText,
                  { type: "secondary" },
                  "今日积分: ",
                ),
                React.createElement(
                  AntText,
                  { strong: true, style: { color: "#52c41a" } },
                  `+${todayRecord.points_earned}`,
                ),
              ),
              React.createElement(
                Col,
                { span: 8 },
                React.createElement(
                  AntText,
                  { type: "secondary" },
                  "连续天数: ",
                ),
                React.createElement(
                  AntText,
                  { strong: true },
                  `${todayRecord.consecutive_days} 天`,
                ),
              ),
              React.createElement(
                Col,
                { span: 8 },
                React.createElement(
                  AntText,
                  { type: "secondary" },
                  "签到时间: ",
                ),
                React.createElement(
                  AntText,
                  null,
                  new Date(todayRecord.created_at).toLocaleTimeString([], { hour12: false }),
                ),
              ),
            ),
          )
        : null,
      // History table
      React.createElement(
        AntText,
        {
          strong: true,
          style: { fontSize: 15, marginBottom: 12, display: "block" },
        },
        "签到记录",
      ),
      React.createElement(Table, {
        dataSource: history,
        columns,
        rowKey: "date",
        loading,
        size: "middle",
        pagination: {
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: ["10", "20", "50"],
          showTotal: (t: number) => `共 ${t} 条`,
          onChange: (p: number, s: number) => {
            setPage(p);
            setPageSize(s);
          },
        },
      }),
  );
}

// ── Locale helper (same pattern as qwenpaw-pet) ──────────────────

function resolvePluginLocale(): string {
  try {
    const lang = localStorage.getItem("language") || "";
    return lang.trim().split("-")[0].toLowerCase();
  } catch {
    return "";
  }
}

// ── Route + menu registration (new API) ──────────────────────────

const _locale = resolvePluginLocale();
const _routeId = `${PLUGIN_ID}:main`;

// Register the page route (independent of menu placement).
window.QwenPaw.route?.add(PLUGIN_ID, {
  id: _routeId,
  path: "/plugin/checkin/main",
  component: CheckinPage,
});

// Add sidebar entry under Agent workspace group (core.workspace-group).
window.QwenPaw.menu?.add(PLUGIN_ID, {
  id: _routeId,
  location: "primary.agentScoped",
  parentId: "core.workspace-group",
  label: _locale === "zh" ? "签到" : "Check-in",
  icon: antdIcons.CalendarOutlined,
  route: _routeId,
  order: 110,
});
