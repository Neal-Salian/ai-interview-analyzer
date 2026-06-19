import { createContext, useContext, useState, type ReactNode, useEffect } from 'react'
import { jwtDecode } from 'jwt-decode'

interface AuthContextType {
    token: string | null
    role: string | null
    login: (token: string) => void
    logout: () => void
    isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
    const [role, setRole] = useState<string | null>(null)

    useEffect(() => {
        if (token) {
            try {
                const decoded: any = jwtDecode(token)
                setRole(decoded.role || null)
            } catch {
                setRole(null)
            }
        } else {
            setRole(null)
        }
    }, [token])

    const login = (newToken: string) => {
        localStorage.setItem('token', newToken)
        setToken(newToken)
    }

    const logout = () => {
        localStorage.removeItem('token')
        setToken(null)
    }

    return (
        <AuthContext.Provider value={{ token, role, login, logout, isAuthenticated: !!token }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const ctx = useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used within AuthProvider')
    return ctx
}