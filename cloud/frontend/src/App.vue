<script setup>
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/Navbar.vue'

const auth = useAuthStore()
</script>

<template>
  <div class="min-h-screen bg-apex-darker">
    <!-- Navbar -->
    <Navbar v-if="auth.isAuthenticated" />

    <!-- Main content -->
    <main :class="auth.isAuthenticated ? 'pt-16' : ''">
      <RouterView />
    </main>
  </div>
</template>

<style>
/* Global scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #1a1a1a;
}

::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
