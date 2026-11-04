import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export interface ProfilePayload {
  predicted_rank: number
  target_districts: string[]
  require_dormitory: boolean
  school_type_preference: string
  top_k: number
  profile_id?: number
}

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

export async function fetchTalentSchools(category: string, items: string[]) {
  const { data } = await api.get('/talents/schools', {
    params: { category, items: items.join(',') },
  })
  return data
}
