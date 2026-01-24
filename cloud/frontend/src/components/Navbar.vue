<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <nav class="fixed top-0 left-0 right-0 h-16 bg-apex-dark/80 backdrop-blur-lg border-b border-apex-border z-50">
    <div class="max-w-7xl mx-auto px-4 h-full flex items-center justify-between">
      <!-- Logo -->
      <router-link to="/chat" class="flex items-center gap-2">
        <span class="text-2xl font-serif font-bold text-gold">Au</span>
        <span class="text-lg font-medium">ApexAurum</span>
      </router-link>

      <!-- Navigation -->
      <div class="flex items-center gap-6">
        <router-link
          to="/chat"
          class="text-gray-400 hover:text-white transition-colors"
          active-class="text-gold"
        >
          Chat
        </router-link>
        <router-link
          to="/agents"
          class="text-gray-400 hover:text-white transition-colors"
          active-class="text-gold"
        >
          Agents
        </router-link>
        <router-link
          to="/village"
          class="text-gray-400 hover:text-white transition-colors"
          active-class="text-gold"
        >
          Village
        </router-link>
        <router-link
          to="/music"
          class="text-gray-400 hover:text-white transition-colors"
          active-class="text-gold"
        >
          Music
        </router-link>
      </div>

      <!-- User menu -->
      <div class="flex items-center gap-4">
        <router-link
          to="/settings"
          class="text-gray-400 hover:text-white transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
          </svg>
        </router-link>

        <button
          @click="handleLogout"
          class="btn-ghost text-sm text-gray-400 hover:text-white"
        >
          Logout
        </button>
      </div>
    </div>
  </nav>
</template>
