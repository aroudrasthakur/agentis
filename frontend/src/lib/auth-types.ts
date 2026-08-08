export interface User {
  id: string;
  email: string;
  display_name: string;
  bio?: string | null;
  organization?: string | null;
  title?: string | null;
  avatar_url?: string | null;
  profile?: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
}

export interface SessionRole {
  assignment_id: string;
  role_id: string;
  role_name: string;
  role_slug: string;
  category: string;
  workspace_id?: string | null;
  workspace_name?: string | null;
}
