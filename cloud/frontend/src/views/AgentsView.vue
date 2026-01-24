<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const agents = ref([])
const loading = ref(true)
const showSpawnModal = ref(false)
const showCouncilModal = ref(false)

// Spawn form
const spawnTask = ref('')
const spawnType = ref('general')
const spawning = ref(false)

// Council form
const councilQuestion = ref('')
const councilAgents = ref(3)
const runningCouncil = ref(false)
const councilResult = ref(null)

const agentTypes = [
  { id: 'general', name: 'General', icon: '🤖', desc: 'General-purpose assistant' },
  { id: 'researcher', name: 'Researcher', icon: '🔬', desc: 'Deep research and analysis' },
  { id: 'coder', name: 'Coder', icon: '💻', desc: 'Code generation and review' },
  { id: 'analyst', name: 'Analyst', icon: '📊', desc: 'Data analysis and insights' },
  { id: 'writer', name: 'Writer', icon: '✍️', desc: 'Content creation and editing' },
]

onMounted(async () => {
  await fetchAgents()
})

async function fetchAgents() {
  loading.value = true
  try {
    const response = await api.get('/api/v1/agents/')
    agents.value = Array.isArray(response.data) ? response.data : []
  } catch (e) {
    console.error('Failed to fetch agents:', e)
    agents.value = []
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return 'Unknown'
  const d = new Date(dateStr)
  return isNaN(d.getTime()) ? 'Unknown' : d.toLocaleString()
}

async function spawnAgent() {
  if (!spawnTask.value.trim()) return

  spawning.value = true
  try {
    const response = await api.post('/api/v1/agents/spawn', {
      task: spawnTask.value,
      agent_type: spawnType.value
    })
    agents.value.unshift(response.data)
    showSpawnModal.value = false
    spawnTask.value = ''
  } catch (e) {
    console.error('Failed to spawn agent:', e)
  } finally {
    spawning.value = false
  }
}

async function runCouncil() {
  if (!councilQuestion.value.trim()) return

  runningCouncil.value = true
  councilResult.value = null
  try {
    const response = await api.post('/api/v1/agents/council', {
      question: councilQuestion.value,
      num_agents: councilAgents.value
    })
    councilResult.value = response.data
  } catch (e) {
    console.error('Failed to run council:', e)
  } finally {
    runningCouncil.value = false
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'running': return 'text-blue-400'
    case 'complete': return 'text-green-400'
    case 'failed': return 'text-red-400'
    default: return 'text-yellow-400'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'running': return '⟳'
    case 'complete': return '✓'
    case 'failed': return '✗'
    default: return '○'
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold">Agents</h1>
        <p class="text-gray-400 mt-1">Spawn and manage background AI agents</p>
      </div>
      <div class="flex gap-3">
        <button @click="showCouncilModal = true" class="btn-secondary">
          🏛️ Socratic Council
        </button>
        <button @click="showSpawnModal = true" class="btn-primary">
          + Spawn Agent
        </button>
      </div>
    </div>

    <!-- Agent Grid -->
    <div v-if="loading" class="text-center py-20 text-gray-400">
      Loading agents...
    </div>

    <div v-else-if="agents.length === 0" class="text-center py-20">
      <div class="text-6xl mb-4">🤖</div>
      <h2 class="text-xl font-bold mb-2">No agents yet</h2>
      <p class="text-gray-400 mb-6">Spawn your first agent to get started</p>
      <button @click="showSpawnModal = true" class="btn-primary">
        Spawn Agent
      </button>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="card hover:border-gold/50 transition-colors"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-2xl">
              {{ agentTypes.find(t => t.id === agent.agent_type)?.icon || '🤖' }}
            </span>
            <span class="font-medium capitalize">{{ agent.agent_type }}</span>
          </div>
          <span :class="getStatusColor(agent.status)" class="text-lg">
            {{ getStatusIcon(agent.status) }}
          </span>
        </div>

        <p class="text-sm text-gray-300 mb-3 line-clamp-2">{{ agent.task }}</p>

        <div class="text-xs text-gray-500">
          {{ formatDate(agent.created_at) }}
        </div>

        <div v-if="agent.result" class="mt-3 pt-3 border-t border-apex-border">
          <div class="text-xs text-gray-500 mb-1">Result:</div>
          <p class="text-sm text-gray-300 line-clamp-3">{{ agent.result }}</p>
        </div>

        <div v-if="agent.error" class="mt-3 pt-3 border-t border-red-500/30">
          <div class="text-xs text-red-400 mb-1">Error:</div>
          <p class="text-sm text-red-300 line-clamp-2">{{ agent.error }}</p>
        </div>
      </div>
    </div>

    <!-- Spawn Modal -->
    <div v-if="showSpawnModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-lg">
        <h2 class="text-xl font-bold mb-4">Spawn Agent</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">Agent Type</label>
            <div class="grid grid-cols-5 gap-2">
              <button
                v-for="type in agentTypes"
                :key="type.id"
                @click="spawnType = type.id"
                class="p-3 rounded-lg text-center transition-all"
                :class="spawnType === type.id
                  ? 'bg-gold/20 ring-1 ring-gold'
                  : 'bg-apex-darker hover:bg-white/5'"
                :title="type.desc"
              >
                <div class="text-2xl">{{ type.icon }}</div>
                <div class="text-xs mt-1">{{ type.name }}</div>
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">Task</label>
            <textarea
              v-model="spawnTask"
              class="input h-32 resize-none"
              placeholder="Describe what you want the agent to do..."
            ></textarea>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button @click="showSpawnModal = false" class="btn-secondary">
            Cancel
          </button>
          <button
            @click="spawnAgent"
            class="btn-primary"
            :disabled="!spawnTask.trim() || spawning"
          >
            {{ spawning ? 'Spawning...' : 'Spawn' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Council Modal -->
    <div v-if="showCouncilModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <h2 class="text-xl font-bold mb-4">🏛️ Socratic Council</h2>
        <p class="text-gray-400 text-sm mb-6">
          Multiple agents will independently consider your question and vote.
        </p>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">Question</label>
            <textarea
              v-model="councilQuestion"
              class="input h-24 resize-none"
              placeholder="What question should the council deliberate?"
            ></textarea>
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">Number of Agents: {{ councilAgents }}</label>
            <input
              type="range"
              v-model="councilAgents"
              min="2"
              max="5"
              class="w-full"
            />
          </div>
        </div>

        <!-- Council Result -->
        <div v-if="councilResult" class="mt-6 p-4 bg-apex-darker rounded-lg">
          <div class="flex items-center gap-2 mb-4">
            <span class="text-2xl">🏛️</span>
            <span class="font-bold">Council Decision</span>
            <span v-if="councilResult.consensus" class="ml-auto bg-green-500/20 text-green-400 px-2 py-1 rounded text-sm">
              Consensus: {{ councilResult.consensus }}
            </span>
          </div>

          <div class="space-y-2">
            <div v-for="(count, option) in councilResult.votes" :key="option" class="flex items-center gap-3">
              <div class="w-24 text-sm">{{ option }}</div>
              <div class="flex-1 h-4 bg-apex-card rounded-full overflow-hidden">
                <div
                  class="h-full bg-gold"
                  :style="{ width: `${(count / councilAgents) * 100}%` }"
                ></div>
              </div>
              <div class="text-sm text-gray-400">{{ count }} votes</div>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button @click="showCouncilModal = false; councilResult = null" class="btn-secondary">
            Close
          </button>
          <button
            @click="runCouncil"
            class="btn-primary"
            :disabled="!councilQuestion.trim() || runningCouncil"
          >
            {{ runningCouncil ? 'Deliberating...' : 'Convene Council' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
