/** Props for the panel controlled by a `Tabs` tab with the same prefix and value. */
export function tabPanelProps(idPrefix: string, value: string) {
  return {
    role: "tabpanel",
    id: `${idPrefix}-panel-${value}`,
    "aria-labelledby": `${idPrefix}-tab-${value}`,
    tabIndex: 0,
  } as const;
}
