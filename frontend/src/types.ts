export interface School {
  id: number
  name: string
  district: string
  school_type: string
  has_dormitory: boolean
  note: string
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
