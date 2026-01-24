<script setup>
import { ref, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    await auth.login(email.value, password.value)
    // Wait for Vue reactivity to propagate
    await nextTick()
    const redirect = route.query.redirect || '/chat'
    await router.push(redirect)
  } catch (e) {
    console.error('Login error:', e)
    error.value = e.response?.data?.detail || e.message || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3 mb-4">
          <span class="text-5xl font-serif font-bold text-gold">Au</span>
        </div>
        <h1 class="text-2xl font-bold">Welcome to ApexAurum</h1>
        <p class="text-gray-400 mt-2">140 Tools. Five Minds. One Village.</p>
      </div>

      <!-- Login Form -->
      <div class="card">
        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- Error -->
          <div v-if="error" class="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm">
            {{ error }}
          </div>

          <!-- Email -->
          <div>
            <label for="email" class="block text-sm font-medium text-gray-300 mb-2">
              Email
            </label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              class="input"
              placeholder="you@example.com"
              :disabled="loading"
            />
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-300 mb-2">
              Password
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              class="input"
              placeholder="Enter your password"
              :disabled="loading"
            />
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="btn-primary w-full"
            :disabled="loading"
          >
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Signing in...
            </span>
            <span v-else>Sign In</span>
          </button>
        </form>

        <!-- Register link -->
        <div class="mt-6 text-center text-sm text-gray-400">
          Don't have an account?
          <router-link to="/register" class="text-gold hover:text-gold-bright">
            Create one
          </router-link>
        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-gray-500 text-xs mt-8">
        The furnace burns eternal.
      </p>
    </div>
  </div>
</template>
