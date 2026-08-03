/** Dashboard routes use client hooks (e.g. useSearchParams); skip static prerender in CI/build. */
export const dynamic = "force-dynamic";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
