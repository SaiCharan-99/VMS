import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Warehouse as WarehouseIcon } from "lucide-react";
import { useState } from "react";
import { api } from "@/api/endpoints";
import { useStations } from "@/api/queries";
import {
  Button,
  Card,
  CardHeader,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  Skeleton,
  useToast,
} from "@/components/ui";

type Kind = "warehouse" | "station";

function CreateDialog({
  kind,
  warehouseId,
  onClose,
}: {
  kind: Kind | null;
  warehouseId?: number;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const toast = useToast();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: (): Promise<unknown> =>
      kind === "warehouse"
        ? api.admin.createWarehouse({ code, name })
        : api.admin.createStation({ warehouse_id: warehouseId ?? 0, code, name }),
    onSuccess: () => {
      toast(`${kind === "warehouse" ? "Warehouse" : "Station"} ${code} created.`);
      void qc.invalidateQueries({ queryKey: ["admin", "warehouses"] });
      void qc.invalidateQueries({ queryKey: ["stations"] });
      close();
    },
  });
  const close = () => {
    setCode("");
    setName("");
    create.reset();
    onClose();
  };
  const noun = kind === "warehouse" ? "warehouse" : "station";
  return (
    <Dialog
      open={kind !== null}
      title={`New ${noun}`}
      onClose={close}
      footer={
        <>
          <Button onClick={close}>Cancel</Button>
          <Button variant="primary" type="submit" form="create-place" loading={create.isPending}>
            Create {noun}
          </Button>
        </>
      }
    >
      <form
        id="create-place"
        className="grid gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Field id="pl-code" label="Code" hint={kind === "warehouse" ? "e.g. BLR-01" : "e.g. ST-3"}>
          <input
            id="pl-code"
            className="input mono"
            required
            maxLength={32}
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </Field>
        <Field id="pl-name" label="Name">
          <input
            id="pl-name"
            className="input"
            required
            maxLength={200}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        {create.isError && (
          <p role="alert" className="m-0 text-sm text-fail">
            {create.error instanceof Error ? create.error.message : "Couldn't create it."}
          </p>
        )}
      </form>
    </Dialog>
  );
}

export function StationsTab() {
  const warehouses = useQuery({ queryKey: ["admin", "warehouses"], queryFn: api.admin.warehouses });
  const stations = useStations();
  const [dialog, setDialog] = useState<{ kind: Kind; warehouseId?: number } | null>(null);

  return (
    <div className="grid gap-4">
      <div className="flex justify-end">
        <Button variant="primary" onClick={() => setDialog({ kind: "warehouse" })}>
          <Plus size={15} aria-hidden />
          New warehouse
        </Button>
      </div>
      {warehouses.isError ? (
        <Card>
          <ErrorState error={warehouses.error} onRetry={() => warehouses.refetch()} />
        </Card>
      ) : warehouses.isPending ? (
        <Skeleton className="h-32 w-full" />
      ) : warehouses.data.length === 0 ? (
        <Card>
          <EmptyState icon={WarehouseIcon} title="No warehouses yet. Add one, then its stations." />
        </Card>
      ) : (
        warehouses.data.map((w) => {
          const own = stations.data?.filter((s) => s.warehouse_id === w.id) ?? [];
          return (
            <Card key={w.id} className="overflow-hidden">
              <CardHeader
                title={
                  <>
                    <span className="mono">{w.code}</span>{" "}
                    <span className="font-normal text-text-2">{w.name}</span>
                  </>
                }
                actions={
                  <Button
                    size="sm"
                    onClick={() => setDialog({ kind: "station", warehouseId: w.id })}
                  >
                    <Plus size={14} aria-hidden />
                    Add station
                  </Button>
                }
              />
              {own.length === 0 ? (
                <p className="m-0 px-[18px] py-3 text-sm text-text-2">No stations yet.</p>
              ) : (
                <ul className="m-0 list-none p-0">
                  {own.map((s) => (
                    <li
                      key={s.id}
                      className="flex gap-3 border-t border-border px-[18px] py-2.5 text-sm first:border-t-0"
                    >
                      <span className="mono w-24 font-medium">{s.code}</span>
                      <span className="text-text-2">{s.name}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          );
        })
      )}
      <CreateDialog
        kind={dialog?.kind ?? null}
        warehouseId={dialog?.warehouseId}
        onClose={() => setDialog(null)}
      />
    </div>
  );
}
