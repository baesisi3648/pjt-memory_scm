export type Severity = 'critical' | 'warning' | 'info';
export type Tier = 'raw_material' | 'equipment' | 'fab' | 'packaging' | 'module';
export type RelationType = 'supplier' | 'customer' | 'partner';
export type UserRole = 'admin' | 'analyst' | 'viewer';

export interface Company {
  id: number;
  name: string;
  name_kr: string;
  cluster_id: number;
  tier: Tier;
  country: string;
  description?: string;
}

export interface Cluster {
  id: number;
  name: string;
  tier: Tier;
  parent_id: number | null;
}

export interface CompanyRelation {
  id: number;
  source_id: number;
  target_id: number;
  relation_type: RelationType;
  strength: number;
}

export interface Alert {
  id: number;
  company_id: number;
  severity: Severity;
  title: string;
  description?: string;
  is_read: boolean;
  created_at: string;
}

export interface AlertRule {
  id: number;
  name: string;
  condition: Record<string, unknown>;
  is_active: boolean;
}

export interface NewsItem {
  id: number;
  title: string;
  url: string;
  source: string;
  company_id: number | null;
  published_at: string;
}

export interface UserFilter {
  id: number;
  name: string;
  company_ids: number[];
  is_default: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
