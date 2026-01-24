<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const library = ref([])
const loading = ref(true)
const showGenerateModal = ref(false)
const generating = ref(false)

// Generate form
const prompt = ref('')
const style = ref('')
const title = ref('')
const selectedModel = ref('V5')

const models = [
  { id: 'V3_5', name: 'V3.5', desc: 'Fast, lower quality' },
  { id: 'V4', name: 'V4', desc: 'Balanced' },
  { id: 'V4_5', name: 'V4.5', desc: 'Better quality' },
  { id: 'V5', name: 'V5', desc: 'Best quality (recommended)' },
]

// Filters
const showFavoritesOnly = ref(false)

onMounted(async () => {
  await fetchLibrary()
})

async function fetchLibrary() {
  loading.value = true
  try {
    const params = new URLSearchParams({ limit: 50 })
    if (showFavoritesOnly.value) {
      params.append('favorites_only', 'true')
    }
    const response = await api.get(`/api/v1/music/library?${params}`)
    library.value = response.data?.tasks || []
  } catch (e) {
    console.error('Failed to fetch library:', e)
    library.value = []
  } finally {
    loading.value = false
  }
}

async function generateMusic() {
  if (!prompt.value.trim()) return

  generating.value = true
  try {
    const response = await api.post('/api/v1/music/generate', {
      prompt: prompt.value,
      style: style.value || null,
      title: title.value || null,
      model: selectedModel.value
    })
    library.value.unshift(response.data)
    showGenerateModal.value = false
    prompt.value = ''
    style.value = ''
    title.value = ''
  } catch (e) {
    console.error('Failed to generate music:', e)
  } finally {
    generating.value = false
  }
}

async function toggleFavorite(task) {
  try {
    await api.patch(`/api/v1/music/${task.id}/favorite`, null, {
      params: { favorite: !task.favorite }
    })
    task.favorite = !task.favorite
  } catch (e) {
    console.error('Failed to toggle favorite:', e)
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'complete': return 'text-green-400'
    case 'processing': return 'text-blue-400'
    case 'failed': return 'text-red-400'
    default: return 'text-yellow-400'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'complete': return '✓'
    case 'processing': return '⟳'
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
        <h1 class="text-3xl font-bold">Music Studio</h1>
        <p class="text-gray-400 mt-1">AI music generation via Suno</p>
      </div>
      <button @click="showGenerateModal = true" class="btn-primary">
        🎵 Generate Music
      </button>
    </div>

    <!-- Filters -->
    <div class="flex gap-4 mb-6">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          v-model="showFavoritesOnly"
          @change="fetchLibrary"
          class="rounded border-apex-border bg-apex-card text-gold focus:ring-gold"
        />
        <span class="text-sm">Favorites only</span>
      </label>
    </div>

    <!-- Library Grid -->
    <div v-if="loading" class="text-center py-20 text-gray-400">
      Loading library...
    </div>

    <div v-else-if="library.length === 0" class="text-center py-20">
      <div class="text-6xl mb-4">🎵</div>
      <h2 class="text-xl font-bold mb-2">No music yet</h2>
      <p class="text-gray-400 mb-6">Generate your first track to get started</p>
      <button @click="showGenerateModal = true" class="btn-primary">
        Generate Music
      </button>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="task in library"
        :key="task.id"
        class="card hover:border-gold/30 transition-colors group"
      >
        <!-- Album art placeholder -->
        <div class="aspect-square bg-gradient-to-br from-apex-dark to-apex-card rounded-lg mb-4 flex items-center justify-center">
          <span class="text-6xl">🎵</span>
        </div>

        <div class="flex items-start justify-between mb-2">
          <div>
            <h3 class="font-medium truncate">{{ task.title || 'Untitled' }}</h3>
            <p class="text-sm text-gray-400 truncate">{{ task.style || 'No style' }}</p>
          </div>
          <button
            @click="toggleFavorite(task)"
            class="text-xl transition-transform hover:scale-110"
          >
            {{ task.favorite ? '⭐' : '☆' }}
          </button>
        </div>

        <p class="text-xs text-gray-500 line-clamp-2 mb-3">{{ task.prompt }}</p>

        <div class="flex items-center justify-between text-xs">
          <span :class="getStatusColor(task.status)">
            {{ getStatusIcon(task.status) }} {{ task.status }}
          </span>
          <span class="text-gray-500">
            ▶ {{ task.play_count }} plays
          </span>
        </div>

        <div v-if="task.agent_id" class="mt-2 text-xs text-gray-500">
          by {{ task.agent_id }}
        </div>

        <!-- Play button (shown on hover for complete tracks) -->
        <button
          v-if="task.status === 'complete'"
          class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-xl"
        >
          <span class="w-16 h-16 bg-gold rounded-full flex items-center justify-center text-apex-dark text-2xl">
            ▶
          </span>
        </button>
      </div>
    </div>

    <!-- Generate Modal -->
    <div v-if="showGenerateModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="card w-full max-w-lg">
        <h2 class="text-xl font-bold mb-4">🎵 Generate Music</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-2">Prompt *</label>
            <textarea
              v-model="prompt"
              class="input h-24 resize-none"
              placeholder="Describe the music you want... e.g., 'An uplifting electronic track with warm synths and a driving beat'"
            ></textarea>
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">Style (optional)</label>
            <input
              v-model="style"
              type="text"
              class="input"
              placeholder="e.g., Electronic, Ambient, Jazz, Lo-fi"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">Title (optional)</label>
            <input
              v-model="title"
              type="text"
              class="input"
              placeholder="Give your track a name"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">Model</label>
            <div class="grid grid-cols-4 gap-2">
              <button
                v-for="model in models"
                :key="model.id"
                @click="selectedModel = model.id"
                class="p-2 rounded-lg text-center text-sm transition-all"
                :class="selectedModel === model.id
                  ? 'bg-gold/20 ring-1 ring-gold'
                  : 'bg-apex-darker hover:bg-white/5'"
                :title="model.desc"
              >
                {{ model.name }}
              </button>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              {{ models.find(m => m.id === selectedModel)?.desc }}
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button @click="showGenerateModal = false" class="btn-secondary">
            Cancel
          </button>
          <button
            @click="generateMusic"
            class="btn-primary"
            :disabled="!prompt.trim() || generating"
          >
            {{ generating ? 'Generating...' : 'Generate' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.group {
  position: relative;
}
</style>
