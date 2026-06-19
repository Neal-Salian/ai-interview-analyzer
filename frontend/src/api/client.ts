import axios from 'axios'

const client = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    withCredentials: true,
})

// Attach JWT token on every request if present
client.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Track whether a refresh is in progress
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

const subscribeTokenRefresh = (cb: (token: string) => void) => {
    refreshSubscribers.push(cb)
}

const onRefreshed = (token: string) => {
    refreshSubscribers.map((cb) => cb(token))
    refreshSubscribers = []
}

// Redirect to login on 401
client.interceptors.response.use(
    (res) => res,
    async (err) => {
        const originalRequest = err.config

        if (err.response?.status === 401 && !originalRequest._retry) {
            if (originalRequest.url === '/auth/refresh') {
                localStorage.removeItem('token')
                window.location.href = '/login'
                return Promise.reject(err)
            }

            if (isRefreshing) {
                return new Promise((resolve) => {
                    subscribeTokenRefresh((token: string) => {
                        originalRequest.headers.Authorization = `Bearer ${token}`
                        resolve(client(originalRequest))
                    })
                })
            }

            originalRequest._retry = true
            isRefreshing = true

            try {
                const res = await client.post('/auth/refresh')
                const newToken = res.data.access_token
                localStorage.setItem('token', newToken)
                isRefreshing = false
                onRefreshed(newToken)
                
                originalRequest.headers.Authorization = `Bearer ${newToken}`
                return client(originalRequest)
            } catch (refreshErr) {
                isRefreshing = false
                localStorage.removeItem('token')
                window.location.href = '/login'
                return Promise.reject(refreshErr)
            }
        }

        return Promise.reject(err)
    }
)

export default client