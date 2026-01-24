<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const searchQuery = ref('')
const searchResults = ref([])
const threads = ref([])
const convergence = ref(null)
const loading = ref(false)
const activeTab = ref('search')

const categories = ['all', 'preferences', 'technical', 'project', 'general']
const selectedCategory = ref('all')

const visibilities = ['all', 'private', 'village', 'bridge']
const selectedVisibility = ref('all')

// Agent filter
const agents = ['all', 'AZOTH', 'ELYSIAN', 'VAJRA', 'KETHER', 'CLAUDE']
const selectedAgent = ref('all')

onMounted(async () => {
  await fetchThreads()
  await checkConvergence()
})

async function search() {
  if (!searchQuery.value.trim()) return

  loading.value = true
  try {
    const params = new URLSearchParams({
      query: searchQuery.value,
      limit: 20
    })

    if (selectedCategory.value !== 'all') {
      params.append('category', selectedCategory.value)
    }
    if (selectedVisibility.value !== 'all') {
      params.append('visibility', selectedVisibility.value)
    }
    if (selectedAgent.value !== 'all') {
      params.append('agent_id', selectedAgent.value)
    }

    const response = await api.get(`/api/v1/village/knowledge?${params}`)
    searchResults.value = response.data?.results || []
  } catch (e) {
    console.error('Search failed:', e)
  } finally {
    loading.value = false
  }
}

async function fetchThreads() {
  try {
    const response = await api.get('/api/v1/village/threads')
    threads.value = response.data?.threads || []
  } catch (e) {
    console.error('Failed to fetch threads:', e)
    threads.value = []
  }
}

async function checkConvergence() {
  try {
    const response = await api.get('/api/v1/village/convergence')
    convergence.value = response.data || null
  } catch (e) {
    console.error('Failed to check convergence:', e)
    convergence.value = null
  }
}

function getAgentColor(agentId) {
  const colors = {
    'AZOTH': 'text-azoth',
    'ELYSIAN': 'text-elysian',
    'VAJRA': 'text-vajra',
    'KETHER': 'text-kether',
    'CLAUDE': 'text-claude'
  }
  return colors[agentId] || 'text-gray-400'
}

function getVisibilityIcon(visibility) {
  switch (visibility) {
    case 'private': return '🔒'
    case 'village': return '🏘️'
    case 'bridge': return '🌉'
    default: return '📄'
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold">Village Memory</h1>
        <p class="text-gray-400 mt-1">Multi-agent shared knowledge with convergence detection</p>
      </div>
    </div>

    <!-- Convergence Alert -->
    <div
      v-if="convergence && convergence.convergence_type !== 'NONE'"
      class="mb-6 p-4 rounded-xl"
      :class="convergence.convergence_type === 'CONSENSUS'
        ? 'bg-green-500/10 border border-green-500/30'
        : 'bg-gold/10 border border-gold/30'"
    >
      <div class="flex items-center gap-3">
        <span class="text-3xl">{{ convergence.convergence_type === 'CONSENSUS' ? '✨' : '🤝' }}</span>
        <div>
          <div class="font-bold">
            {{ convergence.convergence_type === 'CONSENSUS' ? 'Consensus Reached!' : 'Harmony Detected' }}
          </div>
          <div class="text-sm text-gray-400">
            {{ convergence.agents?.join(', ') || 'Agents' }} agree on: {{ convergence.topic }}
          </div>
        </div>
        <div class="ml-auto text-2xl font-bold">
          {{ Math.round(convergence.similarity * 100) }}%
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-6 border-b border-apex-border">
      <button
        @click="activeTab = 'search'"
        class="pb-3 px-2 transition-colors"
        :class="activeTab === 'search' ? 'text-gold border-b-2 border-gold' : 'text-gray-400 hover:text-white'"
      >
        🔍 Search
      </button>
      <button
        @click="activeTab = 'threads'"
        class="pb-3 px-2 transition-colors"
        :class="activeTab === 'threads' ? 'text-gold border-b-2 border-gold' : 'text-gray-400 hover:text-white'"
      >
        💬 Threads
      </button>
    </div>

    <!-- Search Tab -->
    <div v-if="activeTab === 'search'">
      <!-- Search Form -->
      <div class="card mb-6">
        <div class="flex gap-4 mb-4">
          <input
            v-model="searchQuery"
            @keyup.enter="search"
            type="text"
            class="input flex-1"
            placeholder="Search village knowledge..."
          />
          <button @click="search" class="btn-primary" :disabled="loading">
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
        </div>

        <!-- Filters -->
        <div class="flex flex-wrap gap-4 text-sm">
          <div>
            <label class="text-gray-500 mr-2">Category:</label>
            <select v-model="selectedCategory" class="bg-apex-darker border border-apex-border rounded px-2 py-1">
              <option v-for="cat in categories" :key="cat" :value="cat">
                {{ cat.charAt(0).toUpperCase() + cat.slice(1) }}
              </option>
            </select>
          </div>

          <div>
            <label class="text-gray-500 mr-2">Visibility:</label>
            <select v-model="selectedVisibility" class="bg-apex-darker border border-apex-border rounded px-2 py-1">
              <option v-for="vis in visibilities" :key="vis" :value="vis">
                {{ vis.charAt(0).toUpperCase() + vis.slice(1) }}
              </option>
            </select>
          </div>

          <div>
            <label class="text-gray-500 mr-2">Agent:</label>
            <select v-model="selectedAgent" class="bg-apex-darker border border-apex-border rounded px-2 py-1">
              <option v-for="agent in agents" :key="agent" :value="agent">
                {{ agent }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- Results -->
      <div v-if="searchResults.length > 0" class="space-y-4">
        <div
          v-for="result in searchResults"
          :key="result.id"
          class="card hover:border-gold/30 transition-colors"
        >
          <div class="flex items-start justify-between mb-2">
            <div class="flex items-center gap-2">
              <span>{{ getVisibilityIcon(result.visibility) }}</span>
              <span :class="getAgentColor(result.agent_id)" class="font-medium">
                {{ result.agent_id || 'Unknown' }}
              </span>
              <span v-if="result.category" class="text-xs bg-apex-darker px-2 py-0.5 rounded">
                {{ result.category }}
              </span>
            </div>
            <div class="text-xs text-gray-500">
              {{ result.access_count }} accesses
            </div>
          </div>

          <p class="text-gray-300">{{ result.content }}</p>

          <div v-if="result.tags?.length" class="flex gap-2 mt-3">
            <span
              v-for="tag in result.tags"
              :key="tag"
              class="text-xs bg-gold/10 text-gold px-2 py-0.5 rounded"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>

      <div v-else-if="searchQuery && !loading" class="text-center py-12 text-gray-400">
        No results found for "{{ searchQuery }}"
      </div>

      <div v-else-if="!searchQuery" class="text-center py-12 text-gray-400">
        Enter a search query to explore village knowledge
      </div>
    </div>

    <!-- Threads Tab -->
    <div v-if="activeTab === 'threads'">
      <div v-if="threads.length > 0" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="thread in threads"
          :key="thread"
          class="card hover:border-gold/30 transition-colors cursor-pointer"
          @click="searchQuery = thread; activeTab = 'search'; search()"
        >
          <div class="flex items-center gap-2">
            <span class="text-xl">💬</span>
            <span class="font-medium">{{ thread }}</span>
          </div>
        </div>
      </div>

      <div v-else class="text-center py-12 text-gray-400">
        No conversation threads yet
      </div>
    </div>
  </div>
</template>
