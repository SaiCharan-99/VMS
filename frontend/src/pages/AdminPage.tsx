import { useSearchParams } from "react-router-dom";
import { Tabs, type TabItem } from "@/components/ui";
import { tabPanelProps } from "@/lib/tabs";
import { ApiKeysTab } from "./admin/ApiKeysTab";
import { AuditTab } from "./admin/AuditTab";
import { StationsTab } from "./admin/StationsTab";
import { UsersTab } from "./admin/UsersTab";

type Tab = "users" | "stations" | "keys" | "audit";

const TABS: TabItem<Tab>[] = [
  { value: "users", label: "Users" },
  { value: "stations", label: "Warehouses & Stations" },
  { value: "keys", label: "API keys" },
  { value: "audit", label: "Audit log" },
];

const PANELS: Record<Tab, () => JSX.Element> = {
  users: UsersTab,
  stations: StationsTab,
  keys: ApiKeysTab,
  audit: AuditTab,
};

export function AdminPage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get("tab");
  const tab: Tab = TABS.some((t) => t.value === raw) ? (raw as Tab) : "users";
  const Panel = PANELS[tab];
  return (
    <>
      <Tabs
        label="Admin sections"
        idPrefix="admin"
        tabs={TABS}
        value={tab}
        onChange={(t) => setParams({ tab: t }, { replace: true })}
      />
      <div {...tabPanelProps("admin", tab)} className="focus-visible:outline-none">
        <Panel />
      </div>
    </>
  );
}
