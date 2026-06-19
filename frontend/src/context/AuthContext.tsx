import { createContext, useContext, useState, type ReactNode, useEffect } from 'react'
import { jwtDecode } from 'jwt-decode'
import client from '../api/client'

interface AuthContextType {
    token: string | null
    role: string | null
    login: (token: string, refreshToken?: string) => void
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

                // Check if token is expired
                if (decoded.exp && decoded.exp * 1000 < Date.now()) {
                    logout()
                    return
                }

                // Set role and other attributes if needed
                setRole(decoded.role || null)
                // Note: is_active is checked on the backend during token generation and refresh.
                // We assume if the token is valid, the user is active, but we can also add it to the JWT if needed.
            } catch (error) {
                console.error("Failed to decode token:", error)
                logout()
            }
        } else {
            setRole(null)
        }
    }, [token])

    const login = (newToken: string, refreshToken?: string) => {
        localStorage.setItem('token', newToken)
        if (refreshToken) {
            localStorage.setItem('refresh_token', refreshToken)
        }
        setToken(newToken)
    }

    const logout = async () => {
        try {
            await client.post('/auth/logout')
        } catch (err) {
            console.error('Logout request failed', err)
        } finally {
            localStorage.removeItem('token')
            localStorage.removeItem('refresh_token')
            setToken(null)
            setRole(null)
        }
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