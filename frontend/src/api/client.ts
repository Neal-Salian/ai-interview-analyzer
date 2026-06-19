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
            console.error('[DEBUG-AUTH] Caught 401 on URL:', originalRequest.url);
            
            // Do not attempt to refresh if the login request itself failed (e.g. invalid credentials)
            // or if the refresh request failed.
            if (originalRequest.url === '/auth/login' || originalRequest.url === '/auth/refresh') {
                if (originalRequest.url === '/auth/refresh') {
                    console.error('[DEBUG-AUTH] /auth/refresh itself failed with 401. Logging out.');
                    localStorage.removeItem('token')
                    localStorage.removeItem('refresh_token')
                    window.location.href = '/login'
                }
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
                console.log('[DEBUG-AUTH] Calling /auth/refresh...');
                const localRefreshToken = localStorage.getItem('refresh_token');
                const res = await client.post('/auth/refresh', {
                    refresh_token: localRefreshToken
                });
                console.log('[DEBUG-AUTH] /auth/refresh succeeded!');
                const newToken = res.data.access_token
                const newRefreshToken = res.data.refresh_token
                localStorage.setItem('token', newToken)
                if (newRefreshToken) {
                    localStorage.setItem('refresh_token', newRefreshToken)
                }
                isRefreshing = false
                onRefreshed(newToken)
                
                originalRequest.headers.Authorization = `Bearer ${newToken}`
                return client(originalRequest)
            } catch (refreshErr) {
                console.error('[DEBUG-AUTH] /auth/refresh failed:', refreshErr);
                isRefreshing = false
                localStorage.removeItem('token')
                localStorage.removeItem('refresh_token')
                window.location.href = '/login'
                return Promise.reject(refreshErr)
            }
        }

        return Promise.reject(err)
    }
)

export default client