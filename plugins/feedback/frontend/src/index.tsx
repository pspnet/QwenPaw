import type * as ReactNS from "react";

const host = window.QwenPaw.host;
const React: typeof ReactNS = host.React;
const antd = host.antd;
const getApiUrl = host.getApiUrl;
const getApiToken = host.getApiToken;
const antdIcons = host.antdIcons;

const {
  Button, message, Typography, Form, Input, Select, Result, Row, Col,
} = antd;
const { Title, Text } = Typography;
const { TextArea } = Input;

const { useState } = React;

const PLUGIN_ID = "feedback";

// ── Constants ────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: "bug", label: "🐛 Bug 报告" },
  { value: "feature", label: "💡 功能建议" },
  { value: "question", label: "❓ 问题咨询" },
];

const PRIORITIES = [
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" },
  { value: "critical", label: "紧急" },
];

// ── Auth helpers ─────────────────────────────────────────────────────

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
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const t = getApiToken?.();
  if (t) headers.Authorization = `Bearer ${t}`;
  const agentId = getSelectedAgentId();
  if (agentId) headers["X-Agent-Id"] = agentId;
  return headers;
}

// ── Page component ───────────────────────────────────────────────────

function FeedbackPage() {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [form] = (Form as any).useForm();

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const res = await fetch(getApiUrl("/feedback"), {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          title: values.title,
          content: values.content,
          category: values.category || "bug",
          priority: values.priority || "medium",
        }),
      });
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
      setSubmitted(true);
    } catch (e: any) {
      if (e?.errorFields) return;
      message.error("提交失败: " + (e?.message || String(e)));
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    form.resetFields();
    setSubmitted(false);
  };

  const h = React.createElement;

  // Success state
  if (submitted) {
    return h(
      "div",
      { style: { padding: 24, maxWidth: 560, margin: "48px auto" } },
      h(Result, {
        status: "success",
        title: "反馈提交成功",
        subTitle: "感谢您的反馈，我们会尽快处理！",
        extra: [
          h(Button, { type: "primary", key: "continue", onClick: handleReset }, "继续提交"),
        ],
      }),
    );
  }

  // Form state
  return h(
    "div",
    { style: { padding: 24, maxWidth: 560 } },
    h(Title, { level: 4, style: { marginBottom: 24 } }, "问题反馈"),
    h(Text, { type: "secondary", style: { display: "block", marginBottom: 24 } },
      "遇到问题或有改进建议？请填写以下表单，我们会认真处理每一条反馈。"),
    h(Form, { form, layout: "vertical", size: "large" },
      h(Row, { gutter: 16 },
        h(Col, { span: 12 },
          h(Form.Item, {
            name: "category",
            label: "问题分类",
            rules: [{ required: true, message: "请选择" }],
            initialValue: "bug",
          },
            h(Select, { options: CATEGORIES, placeholder: "选择分类" }),
          ),
        ),
        h(Col, { span: 12 },
          h(Form.Item, {
            name: "priority",
            label: "优先级",
            rules: [{ required: true, message: "请选择" }],
            initialValue: "medium",
          },
            h(Select, { options: PRIORITIES, placeholder: "选择优先级" }),
          ),
        ),
      ),
      h(Form.Item, {
        name: "title",
        label: "标题",
        rules: [{ required: true, message: "请输入反馈标题" }],
      },
        h(Input, { placeholder: "一句话概括问题", maxLength: 100, showCount: true }),
      ),
      h(Form.Item, {
        name: "content",
        label: "详细描述",
        rules: [{ required: true, message: "请输入反馈内容" }],
      },
        h(TextArea, { rows: 6, placeholder: "详细描述您遇到的问题或建议...", showCount: true, maxLength: 2000 }),
      ),
      h(Form.Item, { style: { marginTop: 8 } },
        h(Button, {
          type: "primary",
          loading: submitting,
          onClick: handleSubmit,
          block: true,
          icon: h(antdIcons.SendOutlined),
        }, "提交反馈"),
      ),
    ),
  );
}

// ── Route + menu registration ────────────────────────────────────────

function resolvePluginLocale(): string {
  try {
    const lang = localStorage.getItem("language") || "";
    return lang.trim().split("-")[0].toLowerCase();
  } catch {
    return "";
  }
}

const _locale = resolvePluginLocale();
const _routeId = `${PLUGIN_ID}:main`;

window.QwenPaw.route?.add(PLUGIN_ID, {
  id: _routeId,
  path: "/plugin/feedback/main",
  component: FeedbackPage,
});

window.QwenPaw.menu?.add(PLUGIN_ID, {
  id: _routeId,
  location: "primary.agentScoped",
  parentId: "core.workspace-group",
  label: _locale === "zh" ? "问题反馈" : "Feedback",
  icon: antdIcons.MessageOutlined,
  route: _routeId,
  order: 120,
});
