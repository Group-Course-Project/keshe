export interface School {
  id: number
  name: string
  district: string
  school_type: string
  has_dormitory: boolean
  note: string
  /** full=有历年位次可参与推荐；knowledge_only / profile_only=仅有外部资料 */
  data_completeness: string
  source_summary: string
  has_rank_data: boolean
  talents: TalentItem[]
}

export interface TalentItem {
  category: string
  item: string
}

export interface TrendPoint {
  year: number
  min_rank: number | null
  status: string
}

export interface Candidate {
  school_id: number
  name: string
  district: string
  school_type: string
  has_dormitory: boolean
  strategy: string
  match_score: number
  ref_rank: number | null
  ref_year: number | null
  years_available: number
  reasons: string[]
  talents: TalentItem[]
}

export interface RecommendResponse {
  冲: Candidate[]
  稳: Candidate[]
  保: Candidate[]
  profile_id?: number
}

export interface ReportResponse {
  profile_id: number
  report_id: number
  content: string
  model: string
  fallback: boolean
}

export interface VolunteerItem {
  order: number
  school_id: number
  name: string
  ref_rank: number | null
  ref_year: number | null
  ratio: number | null
  strategy: string | null
}

export interface VolunteerCheckResponse {
  items: VolunteerItem[]
  issues: string[]
  counts: { 冲: number; 稳: number; 保: number }
  ratio: { 冲: number; 稳: number; 保: number }
  profile_id?: number
}

export interface ReportListItem {
  id: number
  profile_id: number
  predicted_rank: number
  model: string
  created_at: string
  preview: string
}

export interface ReportDetail {
  id: number
  profile_id: number
  predicted_rank: number | null
  model: string
  prompt_version: string
  content: string
  created_at: string
}

export interface TierStat {
  count: number
  hit: number
  hit_rate: number | null
}

export interface BacktestResponse {
  default_rules: Record<string, [number, number]>
  default: {
    tiers: Record<string, TierStat>
    years: Record<string, Record<string, TierStat>>
  }
  top_sets: {
    rules: Record<string, [number, number]>
    hit_rate: Record<string, number | null>
    score: number
  }[]
}

export interface TalentSchoolsResponse {
  notice: string
  schools: {
    id: number
    name: string
    district: string
    school_type: string
    has_dormitory: boolean
    talents: TalentItem[]
  }[]
}

// ---------------- v0.3 用户体系 ----------------
export interface User {
  id: number
  username: string
  display_name: string
  created_at: string
}

export interface AuthResponse {
  token: string
  user: User
}

// ---------------- v0.3 多套志愿方案 ----------------
export interface PlanProfile {
  predicted_rank?: number
  target_districts?: string[]
  require_dormitory?: boolean
  school_type_preference?: string
  top_k?: number
  profile_id?: number
}

export interface PlanVolunteer {
  order: number
  school_id: number
  name: string
  strategy?: string | null
  ref_rank?: number | null
  ref_year?: number | null
  match_score?: number
  district?: string
  school_type?: string
}

export interface PlanSummary {
  counts?: { 冲: number; 稳: number; 保: number }
  issues?: string[]
  profile_id?: number
}

export interface Plan {
  id: number
  name: string
  profile: PlanProfile
  volunteers: PlanVolunteer[]
  summary: PlanSummary
  share_token: string | null
  created_at: string
  updated_at: string
}

export interface PlanPayload {
  name: string
  profile: PlanProfile
  volunteers: PlanVolunteer[]
  summary: PlanSummary
}

export interface SharedPlan {
  name: string
  owner: string
  profile: PlanProfile
  volunteers: PlanVolunteer[]
  summary: PlanSummary
  created_at: string
  disclaimer: string
}

// ---------------- v0.3 学校对比 ----------------
export interface CompareStats {
  latest_year: number | null
  latest_rank: number | null
  median_rank: number | null
  best_rank: number | null
  worst_rank: number | null
  years_available: number
  estimated_years: number
}

export interface CompareSchool {
  id: number
  name: string
  district: string
  school_type: string
  has_dormitory: boolean
  note: string
  data_completeness: string
  source_summary: string
  has_rank_data: boolean
  talents: TalentItem[]
  trend: TrendPoint[]
  stats: CompareStats
}

export interface CompareResponse {
  schools: CompareSchool[]
  notice: string
}

// ---------------- v0.6 学校档案 ----------------
export interface DetailSection<T = unknown> {
  available: boolean
  reason: string
  items?: T[]
  [key: string]: unknown
}

export interface RankItem {
  year: number
  min_rank: number | null
  status: string
  raw_value: string
}

export interface RankStats {
  latest_year: number | null
  latest_rank: number | null
  median_rank: number | null
  best_rank: number | null
  worst_rank: number | null
  years_available: number
  estimated_years: number
}

export interface AdmissionLineItem {
  year: number
  full_score: number
  unified_line: number | null
  transfer_line: number | null
  score_rate: number | null
  school_level: string
  school_nature: string
  batch: string
  match_status: string
  source_id: string
  credibility: string
  note: string
}

export interface AdmissionScale {
  full_score: number
  years: string
  items: AdmissionLineItem[]
}

export interface EnrollmentPlanItem {
  year: number
  school_nature: string
  plan_total: number | null
  unified_plan: number | null
  directed_plan: number | null
  sport_talent_plan: number | null
  art_talent_plan: number | null
  feature_classes: string
  sport_items: string
  art_items: string
  single_plan: string
  source_id: string
  credibility: string
  note: string
}

export interface ProfileField {
  label: string
  value: string
}

export interface DetailSource {
  id: string
  name: string
  url: string
  kind: string
  credibility: string
  note: string
}

export interface SchoolDetail {
  school: {
    id: number
    name: string
    district: string
    school_type: string
    dormitory_text: string
    dormitory_note: string
    data_completeness: string
    has_rank_data: boolean
    source_summary: string
    note: string
    aliases: string[]
  }
  sections: {
    rank: DetailSection<RankItem> & { stats: RankStats }
    admission_lines: DetailSection & {
      scales: AdmissionScale[]
      total: number
      notice: string
    }
    enrollment_plan: DetailSection<EnrollmentPlanItem>
    talents: DetailSection<TalentItem>
    profile: DetailSection<ProfileField> & {
      fields: ProfileField[]
      source_url: string
      credibility: string
      notice: string
    }
  }
  sources: DetailSource[]
  coverage: { total: number; available: number; missing: string[] }
  disclaimer: string
}

// 导出卡片使用的统一数据结构
export interface ExportCardData {
  title: string
  owner?: string
  predictedRank?: number
  preferences?: string
  volunteers: PlanVolunteer[]
  summary?: PlanSummary
  footnote?: string
}
