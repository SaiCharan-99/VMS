import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Users } from "lucide-react";
import { useState, type FormEvent } from "react";
import { api, type UserInput, type UserPatch } from "@/api/endpoints";
import { useAuth } from "@/auth/AuthProvider";
import {
  Button,
  Card,
  CardHeader,
  DataTable,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  useToast,
  type Column,
} from "@/components/ui";
import { formatWhen } from "@/lib/format";
import type { Role, User, Warehouse } from "@/types/api";

const ROLES: Role[] = ["operator", "reviewer", "admin"];
const ROLE_LABEL: Record<Role, string> = {
  operator: "Operator",
  reviewer: "Reviewer",
  admin: "Admin",
};

function useWarehouses() {
  return useQuery({ queryKey: ["admin", "warehouses"], queryFn: api.admin.warehouses });
}

function WarehouseSelect({
  id,
  value,
  onChange,
  warehouses,
}: {
  id: string;
  value: number | null;
  onChange: (v: number | null) => void;
  warehouses: Warehouse[] | undefined;
}) {
  return (
    <select
      id={id}
      className="select"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
    >
      <option value="">None</option>
      {warehouses?.map((w) => (
        <option key={w.id} value={w.id}>
          {w.code} · {w.name}
        </option>
      ))}
    </select>
  );
}

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong.";
}

function CreateUserDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const warehouses = useWarehouses();
  const blank: UserInput = {
    email: "",
    name: "",
    password: "",
    role: "operator",
    warehouse_id: null,
  };
  const [form, setForm] = useState<UserInput>(blank);
  const create = useMutation({
    mutationFn: () => api.admin.createUser(form),
    onSuccess: (u) => {
      toast(`Created ${u.email}. Share the password with them securely.`);
      void qc.invalidateQueries({ queryKey: ["admin", "users"] });
      setForm(blank);
      onClose();
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <Dialog
      open={open}
      title="New user"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" type="submit" form="create-user" loading={create.isPending}>
            Create user
          </Button>
        </>
      }
    >
      <form id="create-user" onSubmit={submit} className="grid gap-3">
        <Field id="cu-email" label="Email">
          <input
            id="cu-email"
            className="input"
            type="email"
            required
            autoComplete="off"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>
        <Field id="cu-name" label="Name">
          <input
            id="cu-name"
            className="input"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </Field>
        <Field id="cu-password" label="Initial password" hint="At least 8 characters.">
          <input
            id="cu-password"
            className="input"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </Field>
        <Field id="cu-role" label="Role">
          <select
            id="cu-role"
            className="select"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
        </Field>
        <Field id="cu-wh" label="Warehouse">
          <WarehouseSelect
            id="cu-wh"
            value={form.warehouse_id ?? null}
            onChange={(v) => setForm({ ...form, warehouse_id: v })}
            warehouses={warehouses.data}
          />
        </Field>
        {create.isError && (
          <p role="alert" className="m-0 text-sm text-fail">
            {errorText(create.error)}
          </p>
        )}
      </form>
    </Dialog>
  );
}

function EditUserDialog({ user, onClose }: { user: User | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const warehouses = useWarehouses();
  const [patch, setPatch] = useState<UserPatch>({});
  const save = useMutation({
    mutationFn: () => {
      const body = { ...patch };
      if (!body.password) delete body.password;
      return api.admin.updateUser(user?.id ?? 0, body);
    },
    onSuccess: (u) => {
      toast(`Saved ${u.email}.`);
      void qc.invalidateQueries({ queryKey: ["admin", "users"] });
      setPatch({});
      onClose();
    },
  });
  if (!user) return null;
  const val = <K extends keyof UserPatch>(k: K, fallback: UserPatch[K]) =>
    k in patch ? patch[k] : fallback;
  const close = () => {
    setPatch({});
    save.reset();
    onClose();
  };
  return (
    <Dialog
      open
      title={`Edit ${user.email}`}
      onClose={close}
      footer={
        <>
          <Button onClick={close}>Cancel</Button>
          <Button variant="primary" type="submit" form="edit-user" loading={save.isPending}>
            Save
          </Button>
        </>
      }
    >
      <form
        id="edit-user"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
        className="grid gap-3"
      >
        <Field id="eu-name" label="Name">
          <input
            id="eu-name"
            className="input"
            required
            value={val("name", user.name) ?? ""}
            onChange={(e) => setPatch({ ...patch, name: e.target.value })}
          />
        </Field>
        <Field id="eu-role" label="Role">
          <select
            id="eu-role"
            className="select"
            value={val("role", user.role)}
            onChange={(e) => setPatch({ ...patch, role: e.target.value as Role })}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABEL[r]}
              </option>
            ))}
          </select>
        </Field>
        <Field id="eu-wh" label="Warehouse">
          <WarehouseSelect
            id="eu-wh"
            value={val("warehouse_id", user.warehouse_id) ?? null}
            onChange={(v) => setPatch({ ...patch, warehouse_id: v })}
            warehouses={warehouses.data}
          />
        </Field>
        <Field id="eu-pw" label="Reset password" hint="Leave empty to keep the current password.">
          <input
            id="eu-pw"
            className="input"
            type="password"
            minLength={8}
            autoComplete="new-password"
            value={patch.password ?? ""}
            onChange={(e) => setPatch({ ...patch, password: e.target.value })}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={val("is_active", user.is_active) ?? true}
            onChange={(e) => setPatch({ ...patch, is_active: e.target.checked })}
          />
          Active (unchecking signs them out and blocks login)
        </label>
        {save.isError && (
          <p role="alert" className="m-0 text-sm text-fail">
            {errorText(save.error)}
          </p>
        )}
      </form>
    </Dialog>
  );
}

export function UsersTab() {
  const { user: me } = useAuth();
  const users = useQuery({ queryKey: ["admin", "users"], queryFn: api.admin.users });
  const warehouses = useWarehouses();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const whCode = new Map(warehouses.data?.map((w) => [w.id, w.code]));

  const columns: Column<User>[] = [
    {
      key: "name",
      header: "Name",
      cell: (u) => (
        <div className="min-w-0">
          <div className="truncate font-medium">
            {u.name}
            {u.id === me?.id && <span className="ml-1.5 text-xs text-text-3">(you)</span>}
          </div>
          <div className="truncate text-xs text-text-2">{u.email}</div>
        </div>
      ),
    },
    {
      key: "role",
      header: "Role",
      cell: (u) => <span className="chip">{ROLE_LABEL[u.role]}</span>,
    },
    {
      key: "wh",
      header: "Warehouse",
      secondary: true,
      cell: (u) => (
        <span className="text-text-2">{u.warehouse_id ? whCode.get(u.warehouse_id) : "—"}</span>
      ),
    },
    {
      key: "login",
      header: "Last login",
      secondary: true,
      cell: (u) => (
        <span className="text-text-2">
          {u.last_login_at ? formatWhen(u.last_login_at) : "Never"}
        </span>
      ),
    },
    {
      key: "active",
      header: "Status",
      cell: (u) =>
        u.is_active ? (
          <span className="text-text-2">Active</span>
        ) : (
          <span className="text-text-3">Deactivated</span>
        ),
    },
  ];

  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="Users"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={15} aria-hidden />
            New user
          </Button>
        }
      />
      {users.isError ? (
        <ErrorState error={users.error} onRetry={() => users.refetch()} />
      ) : (
        <DataTable
          caption="Users"
          columns={columns}
          rows={users.data?.items.filter((u) => u.email !== "system@vms.local")}
          rowKey={(u) => u.id}
          loading={users.isPending}
          onRowClick={setEditing}
          rowLabel={(u) => `Edit ${u.email}`}
          empty={<EmptyState icon={Users} title="No users yet." />}
        />
      )}
      <CreateUserDialog open={creating} onClose={() => setCreating(false)} />
      <EditUserDialog key={editing?.id ?? 0} user={editing} onClose={() => setEditing(null)} />
    </Card>
  );
}
