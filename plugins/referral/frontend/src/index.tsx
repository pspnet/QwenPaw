// React and antd are injected by the QwenPaw console host at runtime;
// vite ``external``s them so nothing here is bundled.
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
const { Text: AntText, Paragraph } = Typography;

const { useState, useEffect, useCallback, useMemo } = React;

const PLUGIN_ID = "referral";

// ── Types ────────────────────────────────────────────────────────────

type MemberInfo = {
  id: string;
  nickname: string;
  referral_code: string;
};

type ReferralRecord = {
  id: string;
  referrer_member_id: string;
  referee_member_id: string;
  referrer_points: number;
  referee_points: number;
  status: string;
  created_at: string;
};

type RewardsInfo = {
  total_referrals: number;
  total_rewards: number;
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

// ── Page component ───────────────────────────────────────────────────

function ReferralPage() {
  const [member, setMember] = useState<MemberInfo | null>(null);
  const [memberLoading, setMemberLoading] = useState(false);
  const [records, setRecords] = useState<ReferralRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [rewards, setRewards] = useState<RewardsInfo>({ total_referrals: 0, total_rewards: 0 });
  const [rewardsLoading, setRewardsLoading] = useState(false);

  // ── Data loading ──

  const loadMember = useCallback(async () => {
    setMemberLoading(true);
    try {
      const d = await apiGet("/referral/me");
      setMember(d.member || null);
    } catch { message.error("加载会员信息失败"); }
    setMemberLoading(false);
  }, []);

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("size", String(pageSize));
      const d = await apiGet(`/referral/records?${params}`);
      setRecords(d.items || []);
      setTotal(d.total || 0);
    } catch { message.error("加载邀请记录失败"); }
    setLoading(false);
  }, [page, pageSize]);

  const loadRewards = useCallback(async () => {
    setRewardsLoading(true);
    try {
      const d = await apiGet("/referral/rewards");
      setRewards({ total_referrals: d.total_referrals || 0, total_rewards: d.total_rewards || 0 });
    } catch { /* ignore */ }
    setRewardsLoading(false);
  }, []);

  useEffect(() => { void loadMember(); void loadRewards(); }, [loadMember, loadRewards]);
  useEffect(() => { void loadRecords(); }, [loadRecords]);

  const refreshAll = useCallback(() => {
    void loadMember(); void loadRewards(); void loadRecords();
  }, [loadMember, loadRewards, loadRecords]);

  // ── Helpers ──

  const invitationLink = useMemo(() => {
    if (!member?.referral_code) return "";
    return `${window.location.origin}/invite?code=${member.referral_code}`;
  }, [member]);

  const formatDateTime = (v: string) => {
    if (!v) return "";
    const d = new Date(v);
    return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour12: false });
  };

  const h = React.createElement;

  const columns = useMemo(
    () => [
      {
        title: "序号", width: 64, align: "center" as const,
        render: (_: any, __: any, i: number) =>
          h(AntText, { type: "secondary" }, String((page - 1) * pageSize + i + 1)),
      },
      {
        title: "被邀请人 ID", dataIndex: "referee_member_id",
        render: (v: string) => h(AntText, { code: true }, v.substring(0, 16) + "..."),
      },
      {
        title: "我的奖励", dataIndex: "referrer_points", width: 120,
        sorter: (a: any, b: any) => a.referrer_points - b.referrer_points,
        render: (v: number) =>
          h(AntText, { strong: true, style: { color: "#52c41a" } }, `+${v}`),
      },
      {
        title: "对方奖励", dataIndex: "referee_points", width: 120,
        render: (v: number) => h(AntText, { style: { color: "#1677ff" } }, `+${v}`),
      },
      {
        title: "状态", dataIndex: "status", width: 100,
        render: (v: string) =>
          h(Tag, { color: v === "completed" ? "success" : "processing" },
            v === "completed" ? "已完成" : v),
      },
      {
        title: "接受时间", dataIndex: "created_at", width: 180,
        sorter: (a: any, b: any) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        render: formatDateTime,
      },
    ],
    [page, pageSize],
  );

  return h("div", { style: { padding: 24 } },

    // ━━━ Header ━━━
    h("div", {
      style: {
        display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 16,
      },
    },
      h(AntText, { strong: true, style: { fontSize: 18 } }, "推荐人"),
      h(Button, { onClick: refreshAll }, "刷新"),
    ),

    // ━━━ Top Card: Stats + Invitation Info ━━━
    h(Card, {
      loading: memberLoading,
      size: "small",
      style: { marginBottom: 24 },
    },
      member ? h("div", null,
        // ── Row 1: Stats at the top ──
        h(Row, { gutter: 0, style: { marginBottom: 24 } },
          h(Col, { span: 12, style: { textAlign: "center" } },
            h(Statistic, {
              title: "已邀请",
              value: rewards.total_referrals,
              loading: rewardsLoading,
              valueStyle: { fontSize: 28 },
              suffix: "人",
            }),
          ),
          h(Col, { span: 12, style: { textAlign: "center", borderLeft: "1px solid #f0f0f0" } },
            h(Statistic, {
              title: "累计奖励",
              value: rewards.total_rewards,
              loading: rewardsLoading,
              valueStyle: { fontSize: 28, color: "#52c41a" },
              suffix: "积分",
            }),
          ),
        ),
        // ── Divider ──
        h("div", { style: { borderTop: "1px solid #f0f0f0", marginBottom: 20 } }),
        // ── Row 2: Invitation link + code (same row) ──
        h(Row, { gutter: 24 },
          h(Col, { span: 12 },
            h(AntText, { type: "secondary", style: { fontSize: 12, display: "block", marginBottom: 4 } }, "邀请链接"),
            h(Paragraph, {
              copyable: { text: invitationLink },
              style: { marginBottom: 0, fontSize: 14, color: "#595959", wordBreak: "break-all" },
            }, invitationLink || "—"),
          ),
          h(Col, { span: 12 },
            h(AntText, { type: "secondary", style: { fontSize: 12, display: "block", marginBottom: 4 } }, "邀请码"),
            h(Paragraph, {
              copyable: { text: member.referral_code },
              style: { marginBottom: 0, fontSize: 14, color: "#595959", fontFamily: "monospace", letterSpacing: 2 },
            }, member.referral_code || "—"),
          ),
        ),
      ) : null,
    ),

    // ━━━ Records Table ━━━
    h(AntText, {
      strong: true,
      style: { fontSize: 15, marginBottom: 12, display: "block" },
    }, "邀请记录"),
    h(Table, {
      dataSource: records,
      columns,
      rowKey: "id",
      loading,
      size: "middle",
      pagination: {
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        pageSizeOptions: ["10", "20", "50"],
        showTotal: (t: number) => `共 ${t} 条`,
        onChange: (p: number, s: number) => { setPage(p); setPageSize(s); },
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
  path: "/plugin/referral/main",
  component: ReferralPage,
});

// Add sidebar entry under Agent workspace group (core.workspace-group).
window.QwenPaw.menu?.add(PLUGIN_ID, {
  id: _routeId,
  location: "primary.agentScoped",
  parentId: "core.workspace-group",
  label: _locale === "zh" ? "推荐人" : "Referral",
  icon: antdIcons.UsergroupAddOutlined,
  route: _routeId,
  order: 120,
});
