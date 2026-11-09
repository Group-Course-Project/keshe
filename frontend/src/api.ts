import axios from 'axios'
import type {
  AuthResponse,
  CompareResponse,
  Plan,
  PlanPayload,
  SharedPlan,
  SchoolDetail,
  User,
} from './types'

export const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

const TOKEN_KEY = 'zk_auth_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

// 所有请求自动携带登录令牌；未登录时保持匿名，后端按可选用户处理
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    const headers = config.headers as unknown as Record<string, string>
    headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface ProfilePayload {
  predicted_rank: number
  target_districts: string[]
  require_dormitory: boolean
  school_type_preference: string
  top_k: number
  profile_id?: number
}

// ---------------- 原有业务接口 ----------------
export async function fetchSchools() {
  const { data } = await api.get('/schools')
  return data
}

export async function fetchRecommend(payload: ProfilePayload) {
  const { data } = await api.post('/recommend', payload)
  return data
}

export async function fetchTrend(schoolId: number) {
  const { data } = await api.get(`/schools/${schoolId}/trend`)
  return data
}

export async function fetchSchoolDetail(schoolId: number): Promise<SchoolDetail> {
  const { data } = await api.get(`/schools/${schoolId}/detail`)
  return data
}

export async function fetchReport(payload: ProfilePayload) {
  const { data } = await api.post('/report', payload)
  return data
}

export async function fetchVolunteerCheck(payload: {
  predicted_rank: number
  school_ids: number[]
  profile_id?: number
}) {
  const { data } = await api.post('/volunteer/check', payload)
  return data
}

export async function fetchReports() {
  const { data } = await api.get('/reports')
  return data
}

export async function fetchReportDetail(reportId: number) {
  const { data } = await api.get(`/reports/${reportId}`)
  return data
}

export async function fetchBacktest() {
  const { data } = await api.get('/backtest')
  return data
}

export async function fetchTalentItems() {
  const { data } = await api.get('/talents/items')
  return data
}

export async function fetchTalentSchools(
  category: string,
  items: string[],
  match: 'any' | 'all' = 'any',
) {
  const { data } = await api.get('/talents/schools', {
    params: { category, items: items.join(','), match },
  })
  return data
}

// ---------------- 账号体系 ----------------
export interface AuthPayload {
  username: string
  password: string
  display_name?: string
}

export async function fetchMe(): Promise<{ user: User | null }> {
  const { data } = await api.get('/auth/me')
  return data
}

export async function authLogin(payload: AuthPayload): Promise<AuthResponse> {
  const { data } = await api.post('/auth/login', payload)
  return data
}

export async function authRegister(payload: AuthPayload): Promise<AuthResponse> {
  const { data } = await api.post('/auth/register', payload)
  return data
}

export async function authLogout(): Promise<void> {
  await api.post('/auth/logout')
}

// ---------------- 多套志愿方案 ----------------
export async function fetchPlans(): Promise<Plan[]> {
  const { data } = await api.get('/plans')
  return data
}

export async function createPlan(payload: PlanPayload): Promise<Plan> {
  const { data } = await api.post('/plans', payload)
  return data
}

export async function updatePlan(id: number, payload: Partial<PlanPayload>): Promise<Plan> {
  const { data } = await api.put(`/plans/${id}`, payload)
  return data
}

export async function deletePlan(id: number): Promise<void> {
  await api.delete(`/plans/${id}`)
}

export async function enableShare(id: number): Promise<{ share_token: string; share_path: string }> {
  const { data } = await api.post(`/plans/${id}/share`)
  return data
}

export async function disableShare(id: number): Promise<void> {
  await api.delete(`/plans/${id}/share`)
}

export async function fetchShare(token: string): Promise<SharedPlan> {
  const { data } = await api.get(`/share/${encodeURIComponent(token)}`)
  return data
}

// ---------------- 学校对比 ----------------
export async function compareSchools(schoolIds: number[]): Promise<CompareResponse> {
  const { data } = await api.post('/schools/compare', { school_ids: schoolIds })
  return data
}

// 统一把后端错误转成可展示文案
export function errorText(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) return '参数填写有误，请检查输入'
    return err.message || '请求失败'
  }
  return err instanceof Error ? err.message : '请求失败'
}
