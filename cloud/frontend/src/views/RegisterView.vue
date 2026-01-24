<script setup>
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters'
    return
  }

  loading.value = true

  try {
    await auth.register(email.value, password.value, displayName.value || null)
    // Wait for Vue reactivity to propagate
    await nextTick()
    await router.push('/chat')
  } catch (e) {
    console.error('Registration error:', e)
    error.value = e.response?.data?.detail || e.message || 'Registration failed'
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
        <h1 class="text-2xl font-bold">Join the Village</h1>
        <p class="text-gray-400 mt-2">Create your ApexAurum account</p>
      </div>

      <!-- Register Form -->
      <div class="card">
        <form @submit.prevent="handleSubmit" class="space-y-5">
          <!-- Error -->
          <div v-if="error" class="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm">
            {{ error }}
          </div>

          <!-- Display Name -->
          <div>
            <label for="displayName" class="block text-sm font-medium text-gray-300 mb-2">
              Display Name <span class="text-gray-500">(optional)</span>
            </label>
            <input
              id="displayName"
              v-model="displayName"
              type="text"
              class="input"
              placeholder="How should we call you?"
              :disabled="loading"
            />
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
              placeholder="At least 8 characters"
              :disabled="loading"
            />
          </div>

          <!-- Confirm Password -->
          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-300 mb-2">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              required
              class="input"
              placeholder="Repeat your password"
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
              Creating account...
            </span>
            <span v-else>Create Account</span>
          </button>
        </form>

        <!-- Login link -->
        <div class="mt-6 text-center text-sm text-gray-400">
          Already have an account?
          <router-link to="/login" class="text-gold hover:text-gold-bright">
            Sign in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
