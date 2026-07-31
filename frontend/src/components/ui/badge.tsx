import { cn } from "@/lib/utils";

export function Badge({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold tracking-wide",
        className
      )}
    >
      {children}
    </span>
  );
}

export function OrgBadge({ org }: { org: "Internal" | "External" }) {
  return (
    <Badge
      className={
        org === "Internal"
          ? "bg-teal-soft text-teal-deep"
          : "bg-coral-soft text-coral-deep"
      }
    >
      {org}
    </Badge>
  );
}
