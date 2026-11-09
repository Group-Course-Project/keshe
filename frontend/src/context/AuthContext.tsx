import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import {
  authLogin,
  authLogout,
  authRegister,
  fetchMe,
  setToken,
  type AuthPayload,
} from '../api'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  ready: boolean
  loginOpen: boolean
  openLogin: () => void
  closeLogin: () => void
  login: (payload: AuthPayload) => Promise<void>
  register: (payload: AuthPayload) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth 必须在 AuthProvider 内使用')
  return value
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)
  const [loginOpen, setLoginOpen] = useState(false)

  useEffect(() => {
    let alive = true
    fetchMe()
      .then(({ user: current }) => {
        // 令牌过期/无效时后端返回 null，顺手清掉本地残留
        if (!current) setToken(null)
        if (alive) setUser(current)
      })
      .catch(() => {
        if (alive) setToken(null)
      })
      .finally(() => {
        if (alive) setReady(true)
      })
    return () => {
      alive = false
    }
  }, [])

  const login = useCallback(async (payload: AuthPayload) => {
    const { token, user: next } = await authLogin(payload)
    setToken(token)
    setUser(next)
  }, [])

  const register = useCallback(async (payload: AuthPayload) => {
    const { token, user: next } = await authRegister(payload)
    setToken(token)
    setUser(next)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authLogout()
    } catch {
      // 即使服务端已失效，也要清掉本地令牌
    } finally {
      setToken(null)
      setUser(null)
    }
  }, [])

  const openLogin = useCallback(() => setLoginOpen(true), [])
  const closeLogin = useCallback(() => setLoginOpen(false), [])

  return (
    <AuthContext.Provider
      value={{
        user,
        ready,
        loginOpen,
        openLogin,
        closeLogin,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
