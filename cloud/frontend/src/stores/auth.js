import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('accessToken'))
  const refreshToken = ref(localStorage.getItem('refreshToken'))

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)

  // Actions
  async function login(email, password) {
    const response = await api.post('/api/v1/auth/login', { email, password })
    setTokens(response.data)
    await fetchProfile()
  }

  async function register(email, password, displayName) {
    const response = await api.post('/api/v1/auth/register', {
      email,
      password,
      display_name: displayName
    })
    setTokens(response.data)
    await fetchProfile()
  }

  async function logout() {
    try {
      await api.post('/api/v1/auth/logout')
    } catch (e) {
      // Ignore errors on logout
    }
    clearTokens()
  }

  async function fetchProfile() {
    if (!accessToken.value) return
    try {
      const response = await api.get('/api/v1/user/profile')
      user.value = response.data
    } catch (e) {
      // Don't clear tokens on profile fetch failure - token might still be valid
      // This prevents logout loops when profile endpoint has issues
      console.error('Failed to fetch profile:', e)
      user.value = null
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      clearTokens()
      return false
    }

    try {
      const response = await api.post('/api/v1/auth/refresh', {
        refresh_token: refreshToken.value
      })
      setTokens(response.data)
      return true
    } catch (e) {
      clearTokens()
      return false
    }
  }

  function setTokens(data) {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('accessToken', data.access_token)
    localStorage.setItem('refreshToken', data.refresh_token)
  }

  function clearTokens() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  // Initialize: try to load profile if we have a token
  if (accessToken.value) {
    fetchProfile()
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    login,
    register,
    logout,
    fetchProfile,
    refreshAccessToken,
  }
})
