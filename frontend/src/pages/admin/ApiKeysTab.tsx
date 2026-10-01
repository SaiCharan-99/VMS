import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Plus } from "lucide-react";
import { useState } from "react";
import { api } from "@/api/endpoints";
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
import type { ApiKey, ApiKeyCreated } from "@/types/api";

function CreateKeyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const create = useMutation({
    mutationFn: () => api.admin.createApiKey(name),
    onSuccess: (k) => {
      setCreated(k);
      void qc.invalidateQueries({ queryKey: ["admin", "api-keys"] });
    },
  });
  const close = () => {
    setName("");
    setCreated(null);
    create.reset();
    onClose();
  };
  const copy = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      toast("Key copied.");
    } catch {
      toast("Couldn't copy. Select the key and copy it by hand.", "error");
    }
  };
  return (
    <Dialog
      open={open}
      title={created ? "Copy your new API key" : "New API key"}
      onClose={close}
      footer={
        created ? (
          <Button variant="primary" onClick={close}>
            Done
          </Button>
        ) : (
          <>
            <Button onClick={close}>Cancel</Button>
            <Button variant="primary" type="submit" form="create-key" loading={create.isPending}>
              Create key
            </Button>
          </>
        )
      }
    >
      {created ? (
        <div className="grid gap-3">
          <p className="m-0 text-sm text-text-2">
            This is the only time the key is shown. Store it in the integration&apos;s secret
            settings now; it acts as an operator and sends <span className="mono">X-API-Key</span>.
          </p>
          <div className="flex items-center gap-2">
            <input
              readOnly
              aria-label="API key"
              className="input mono min-w-0 flex-1"
              value={created.key}
              onFocus={(e) => e.target.select()}
            />
            <Button onClick={() => void copy()}>
              <Copy size={15} aria-hidden />
              Copy
            </Button>
          </div>
        </div>
      ) : (
        <form
          id="create-key"
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <Field id="key-name" label="Name" hint="Who or what uses it, e.g. “WMS integration”.">
            <input
              id="key-name"
              className="input"
              required
              maxLength={200}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>
          {create.isError && (
            <p role="alert" className="m-0 text-sm text-fail">
              {create.error instanceof Error ? create.error.message : "Couldn't create the key."}
            </p>
          )}
        </form>
      )}
    </Dialog>
  );
}

export function ApiKeysTab() {
  const qc = useQueryClient();
  const toast = useToast();
  const keys = useQuery({ queryKey: ["admin", "api-keys"], queryFn: api.admin.apiKeys });
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState<ApiKey | null>(null);
  const revoke = useMutation({
    mutationFn: (id: number) => api.admin.revokeApiKey(id),
    onSuccess: () => {
      toast(`Revoked “${revoking?.name}”.`);
      void qc.invalidateQueries({ queryKey: ["admin", "api-keys"] });
      setRevoking(null);
    },
    onError: (err) => toast(err instanceof Error ? err.message : "Couldn't revoke it.", "error"),
  });

  const columns: Column<ApiKey>[] = [
    { key: "name", header: "Name", cell: (k) => <span className="font-medium">{k.name}</span> },
    {
      key: "created",
      header: "Created",
      secondary: true,
      cell: (k) => <span className="text-text-2">{formatWhen(k.created_at)}</span>,
    },
    {
      key: "status",
      header: "Status",
      cell: (k) =>
        k.revoked_at ? (
          <span className="text-text-3">Revoked {formatWhen(k.revoked_at)}</span>
        ) : (
          <span className="text-text-2">Active</span>
        ),
    },
    {
      key: "actions",
      header: "",
      numeric: true,
      cell: (k) =>
        k.revoked_at ? null : (
          <Button size="sm" variant="ghost" onClick={() => setRevoking(k)}>
            Revoke
          </Button>
        ),
    },
  ];

  return (
    <Card className="overflow-hidden">
      <CardHeader
        title="API keys"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={15} aria-hidden />
            New key
          </Button>
        }
      />
      {keys.isError ? (
        <ErrorState error={keys.error} onRetry={() => keys.refetch()} />
      ) : (
        <DataTable
          caption="API keys"
          columns={columns}
          rows={keys.data}
          rowKey={(k) => k.id}
          loading={keys.isPending}
          empty={<EmptyState icon={KeyRound} title="No API keys yet." />}
        />
      )}
      <CreateKeyDialog open={creating} onClose={() => setCreating(false)} />
      <Dialog
        open={revoking !== null}
        title="Revoke API key?"
        onClose={() => setRevoking(null)}
        footer={
          <>
            <Button onClick={() => setRevoking(null)}>Cancel</Button>
            <Button
              variant="fail"
              loading={revoke.isPending}
              onClick={() => revoking && revoke.mutate(revoking.id)}
            >
              Revoke
            </Button>
          </>
        }
      >
        <p className="m-0 text-sm text-text-2">
          “{revoking?.name}” stops working immediately. This can&apos;t be undone; create a new key
          if you need one again.
        </p>
      </Dialog>
    </Card>
  );
}
