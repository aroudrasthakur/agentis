import { Badge } from "@/components/ui/badge";

const LABELS: Record<string, string> = {
  baseline: "Baseline",
  system_admin: "System administration",
  functional: "Functional",
  gathering_access: "Gathering access",
  resource_access: "Resource access",
  service: "Service",
  legacy: "Deprecated legacy",
};

export function RoleCategoryBadge({ category }: { category?: string }) {
  if (!category) return null;
  return (
    <Badge className="bg-teal-soft/80 text-teal-deep">{LABELS[category] ?? category}</Badge>
  );
}
