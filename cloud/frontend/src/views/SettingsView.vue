<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

const auth = useAuthStore()

const displayName = ref('')
const loading = ref(false)
const saved = ref(false)
const usage = ref(null)
const preferences = ref({
  default_model: 'claude-sonnet-4-5-20250514',
  cache_strategy: 'balanced',
  context_strategy: 'adaptive',
  theme: 'dark',
  default_agent: 'AZOTH'
})

const models = [
  { id: 'claude-sonnet-4-5-20250514', name: 'Sonnet 4.5' },
  { id: 'claude-opus-4-5-20251001', name: 'Opus 4.5' },
  { id: 'claude-haiku-4-5-20251001', name: 'Haiku 4.5' },
]

const cacheStrategies = [
  { id: 'disabled', name: 'Disabled' },
  { id: 'conservative', name: 'Conservative' },
  { id: 'balanced', name: 'Balanced' },
  { id: 'aggressive', name: 'Aggressive' },
]

const contextStrategies = [
  { id: 'disabled', name: 'Disabled' },
  { id: 'balanced', name: 'Balanced' },
  { id: 'adaptive', name: 'Adaptive' },
  { id: 'aggressive', name: 'Aggressive' },
  { id: 'rolling', name: 'Rolling' },
]

const agents = ['AZOTH', 'ELYSIAN', 'VAJRA', 'KETHER', 'CLAUDE']

onMounted(async () => {
  displayName.value = auth.user?.display_name || ''
  await fetchPreferences()
  await fetchUsage()
})

async function fetchPreferences() {
  try {
    const response = await api.get('/api/v1/user/preferences')
    preferences.value = { ...preferences.value, ...response.data }
  } catch (e) {
    console.error('Failed to fetch preferences:', e)
  }
}

async function fetchUsage() {
  try {
    const response = await api.get('/api/v1/user/usage')
    usage.value = response.data
  } catch (e) {
    console.error('Failed to fetch usage:', e)
  }
}

async function saveProfile() {
  loading.value = true
  saved.value = false
  try {
    await api.put('/api/v1/user/profile', {
      display_name: displayName.value
    })
    auth.user.display_name = displayName.value
    saved.value = true
    setTimeout(() => saved.value = false, 3000)
  } catch (e) {
    console.error('Failed to save profile:', e)
  } finally {
    loading.value = false
  }
}

async function savePreferences() {
  loading.value = true
  saved.value = false
  try {
    await api.put('/api/v1/user/preferences', preferences.value)
    saved.value = true
    setTimeout(() => saved.value = false, 3000)
  } catch (e) {
    console.error('Failed to save preferences:', e)
  } finally {
    loading.value = false
  }
}

function formatCost(cost) {
  return `$${cost.toFixed(4)}`
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-8">Settings</h1>

    <!-- Success message -->
    <div
      v-if="saved"
      class="mb-6 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm"
    >
      Settings saved successfully!
    </div>

    <!-- Profile Section -->
    <div class="card mb-6">
      <h2 class="text-xl font-bold mb-4">Profile</h2>

      <div class="space-y-4">
        <div>
          <label class="block text-sm text-gray-400 mb-2">Email</label>
          <input
            type="email"
            :value="auth.user?.email"
            disabled
            class="input bg-apex-darker cursor-not-allowed"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Display Name</label>
          <input
            v-model="displayName"
            type="text"
            class="input"
            placeholder="How should we call you?"
          />
        </div>

        <button
          @click="saveProfile"
          class="btn-primary"
          :disabled="loading"
        >
          {{ loading ? 'Saving...' : 'Save Profile' }}
        </button>
      </div>
    </div>

    <!-- Preferences Section -->
    <div class="card mb-6">
      <h2 class="text-xl font-bold mb-4">Preferences</h2>

      <div class="space-y-4">
        <div>
          <label class="block text-sm text-gray-400 mb-2">Default Model</label>
          <select v-model="preferences.default_model" class="input">
            <option v-for="model in models" :key="model.id" :value="model.id">
              {{ model.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Default Agent</label>
          <select v-model="preferences.default_agent" class="input">
            <option v-for="agent in agents" :key="agent" :value="agent">
              {{ agent }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Cache Strategy</label>
          <select v-model="preferences.cache_strategy" class="input">
            <option v-for="s in cacheStrategies" :key="s.id" :value="s.id">
              {{ s.name }}
            </option>
          </select>
          <p class="text-xs text-gray-500 mt-1">
            Higher caching = more cost savings but potentially stale responses
          </p>
        </div>

        <div>
          <label class="block text-sm text-gray-400 mb-2">Context Strategy</label>
          <select v-model="preferences.context_strategy" class="input">
            <option v-for="s in contextStrategies" :key="s.id" :value="s.id">
              {{ s.name }}
            </option>
          </select>
          <p class="text-xs text-gray-500 mt-1">
            How to handle long conversations approaching token limits
          </p>
        </div>

        <button
          @click="savePreferences"
          class="btn-primary"
          :disabled="loading"
        >
          {{ loading ? 'Saving...' : 'Save Preferences' }}
        </button>
      </div>
    </div>

    <!-- Usage Section -->
    <div class="card">
      <h2 class="text-xl font-bold mb-4">Usage Statistics</h2>

      <div v-if="usage" class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div class="bg-apex-darker rounded-lg p-4">
          <div class="text-2xl font-bold text-gold">{{ usage.total_messages }}</div>
          <div class="text-sm text-gray-400">Messages</div>
        </div>

        <div class="bg-apex-darker rounded-lg p-4">
          <div class="text-2xl font-bold text-gold">{{ usage.conversations_count }}</div>
          <div class="text-sm text-gray-400">Conversations</div>
        </div>

        <div class="bg-apex-darker rounded-lg p-4">
          <div class="text-2xl font-bold text-gold">{{ usage.agents_spawned }}</div>
          <div class="text-sm text-gray-400">Agents Spawned</div>
        </div>

        <div class="bg-apex-darker rounded-lg p-4">
          <div class="text-2xl font-bold text-gold">{{ usage.music_generated }}</div>
          <div class="text-sm text-gray-400">Music Generated</div>
        </div>

        <div class="bg-apex-darker rounded-lg p-4">
          <div class="text-2xl font-bold text-gold">{{ (usage.total_tokens / 1000).toFixed(1) }}K</div>
          <div class="text-sm text-gray-400">Tokens Used</div>
        </div>

        <div class="bg-apex-darker rounded-lg p-4">
          <div class="text-2xl font-bold text-gold">{{ formatCost(usage.total_cost_usd) }}</div>
          <div class="text-sm text-gray-400">Total Cost</div>
        </div>
      </div>

      <div v-else class="text-center py-8 text-gray-400">
        Loading usage statistics...
      </div>
    </div>

    <!-- Danger Zone -->
    <div class="card mt-6 border-red-500/30">
      <h2 class="text-xl font-bold text-red-400 mb-4">Danger Zone</h2>
      <p class="text-sm text-gray-400 mb-4">
        These actions are irreversible. Please be careful.
      </p>
      <button class="btn bg-red-500/20 text-red-400 border border-red-500/50 hover:bg-red-500/30">
        Delete Account
      </button>
    </div>
  </div>
</template>
