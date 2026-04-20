'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { getMe, UserResponse } from '@/lib/api'

interface AuthContextType {
  user: UserResponse | null
  token: string | null
  isLoading: boolean
  setToken: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  setToken: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [token, setTokenState] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('lexquery_token')
    if (stored) {
      setTokenState(stored)
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('lexquery_token')
          setTokenState(null)
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const setToken = (t: string) => {
    localStorage.setItem('lexquery_token', t)
    setTokenState(t)
    getMe().then(setUser).catch(() => {})
  }

  const logout = () => {
    localStorage.removeItem('lexquery_token')
    setTokenState(null)
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, setToken, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
