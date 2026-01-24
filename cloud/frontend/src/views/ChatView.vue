<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { marked } from 'marked'

const route = useRoute()
const router = useRouter()
const chat = useChatStore()

const inputMessage = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)
const showSidebar = ref(true)

// Agent selector
const agents = [
  { id: 'AZOTH', name: 'Azoth', color: 'azoth', symbol: '∴' },
  { id: 'ELYSIAN', name: 'Elysian', color: 'elysian', symbol: '∴' },
  { id: 'VAJRA', name: 'Vajra', color: 'vajra', symbol: '∴' },
  { id: 'KETHER', name: 'Kether', color: 'kether', symbol: '∴' },
  { id: 'CLAUDE', name: 'Claude', color: 'claude', symbol: '' },
]
const selectedAgent = ref('AZOTH')

// Load conversation if ID in route
onMounted(async () => {
  await chat.fetchConversations()

  if (route.params.id) {
    await chat.loadConversation(route.params.id)
  }

  inputRef.value?.focus()
})

// Watch for route changes
watch(() => route.params.id, async (newId) => {
  if (newId) {
    await chat.loadConversation(newId)
  } else {
    chat.createConversation()
  }
})

// Auto-scroll on new messages
watch(() => chat.messages.length, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
})

async function handleSubmit() {
  const message = inputMessage.value.trim()
  if (!message || chat.isStreaming) return

  inputMessage.value = ''
  await chat.sendMessage(message)
}

function newConversation() {
  chat.createConversation()
  router.push('/chat')
}

function selectConversation(conv) {
  router.push(`/chat/${conv.id}`)
}

function renderMarkdown(content) {
  return marked(content, { breaks: true })
}
</script>

<template>
  <div class="flex h-[calc(100vh-4rem)]">
    <!-- Sidebar -->
    <aside
      v-show="showSidebar"
      class="w-72 bg-apex-dark border-r border-apex-border flex flex-col"
    >
      <!-- New Chat Button -->
      <div class="p-4">
        <button
          @click="newConversation"
          class="btn-primary w-full flex items-center justify-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          New Chat
        </button>
      </div>

      <!-- Conversations List -->
      <div class="flex-1 overflow-y-auto px-2">
        <div
          v-for="conv in chat.sortedConversations"
          :key="conv.id"
          @click="selectConversation(conv)"
          class="group px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="chat.currentConversation?.id === conv.id
            ? 'bg-gold/20 text-gold'
            : 'hover:bg-white/5 text-gray-300'"
        >
          <div class="flex items-center justify-between">
            <span class="truncate text-sm">
              {{ conv.title || 'New Conversation' }}
            </span>
            <span v-if="conv.favorite" class="text-gold text-xs">★</span>
          </div>
          <div class="text-xs text-gray-500 mt-1">
            {{ new Date(conv.updated_at).toLocaleDateString() }}
          </div>
        </div>

        <div v-if="chat.conversations.length === 0" class="text-center text-gray-500 text-sm py-8">
          No conversations yet
        </div>
      </div>

      <!-- Agent Selector -->
      <div class="p-4 border-t border-apex-border">
        <label class="block text-xs text-gray-500 mb-2">Active Agent</label>
        <div class="grid grid-cols-5 gap-1">
          <button
            v-for="agent in agents"
            :key="agent.id"
            @click="selectedAgent = agent.id"
            class="p-2 rounded text-center transition-all text-xs"
            :class="selectedAgent === agent.id
              ? `bg-${agent.color}/20 text-${agent.color} ring-1 ring-${agent.color}`
              : 'hover:bg-white/5 text-gray-400'"
            :title="agent.name"
          >
            {{ agent.symbol }}{{ agent.name.charAt(0) }}
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="flex-1 flex flex-col bg-apex-darker">
      <!-- Toggle Sidebar (mobile) -->
      <button
        @click="showSidebar = !showSidebar"
        class="md:hidden absolute top-20 left-2 z-10 p-2 bg-apex-card rounded-lg"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
        </svg>
      </button>

      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto px-4 py-6"
      >
        <div class="max-w-3xl mx-auto space-y-6">
          <!-- Welcome message if no messages -->
          <div v-if="chat.messages.length === 0" class="text-center py-20">
            <div class="text-6xl font-serif font-bold text-gold mb-4">Au</div>
            <h2 class="text-2xl font-bold mb-2">Welcome to ApexAurum Cloud</h2>
            <p class="text-gray-400 mb-8">140 Tools. Five Minds. One Village.</p>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-xl mx-auto text-sm">
              <button
                @click="inputMessage = 'What can you help me with?'"
                class="btn-secondary text-left"
              >
                What can you do?
              </button>
              <button
                @click="inputMessage = 'Tell me about the Village Protocol'"
                class="btn-secondary text-left"
              >
                Village Protocol
              </button>
              <button
                @click="inputMessage = 'Generate some music for me'"
                class="btn-secondary text-left"
              >
                Generate Music
              </button>
              <button
                @click="inputMessage = 'Spawn a research agent'"
                class="btn-secondary text-left"
              >
                Spawn Agent
              </button>
            </div>
          </div>

          <!-- Message list -->
          <div
            v-for="message in chat.messages"
            :key="message.id"
            class="flex gap-4"
            :class="message.role === 'user' ? 'justify-end' : ''"
          >
            <!-- Avatar -->
            <div
              v-if="message.role !== 'user'"
              class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
              :class="message.role === 'system' ? 'bg-red-500/20' : 'bg-gold/20'"
            >
              <span v-if="message.role === 'assistant'" class="text-gold font-serif font-bold text-sm">Au</span>
              <span v-else class="text-red-400 text-sm">!</span>
            </div>

            <!-- Message content -->
            <div
              class="max-w-[80%] rounded-2xl px-4 py-3"
              :class="{
                'bg-gold text-apex-dark': message.role === 'user',
                'bg-apex-card': message.role === 'assistant',
                'bg-red-500/10 border border-red-500/30': message.role === 'system'
              }"
            >
              <div
                v-if="message.role === 'assistant'"
                class="prose prose-invert prose-sm max-w-none"
                v-html="renderMarkdown(message.content)"
              />
              <div v-else>{{ message.content }}</div>
            </div>

            <!-- User avatar -->
            <div
              v-if="message.role === 'user'"
              class="w-8 h-8 rounded-full bg-gradient-to-br from-gold to-gold-dim flex items-center justify-center flex-shrink-0"
            >
              <span class="text-apex-dark font-bold text-sm">Y</span>
            </div>
          </div>

          <!-- Streaming indicator -->
          <div v-if="chat.isStreaming" class="flex gap-4">
            <div class="w-8 h-8 rounded-full bg-gold/20 flex items-center justify-center flex-shrink-0">
              <span class="text-gold font-serif font-bold text-sm">Au</span>
            </div>
            <div class="bg-apex-card rounded-2xl px-4 py-3">
              <div class="flex items-center gap-2 text-gray-400">
                <div class="flex gap-1">
                  <span class="w-2 h-2 bg-gold rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                  <span class="w-2 h-2 bg-gold rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                  <span class="w-2 h-2 bg-gold rounded-full animate-bounce" style="animation-delay: 300ms"></span>
                </div>
                <span class="text-sm">Thinking...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="border-t border-apex-border p-4">
        <form @submit.prevent="handleSubmit" class="max-w-3xl mx-auto">
          <div class="flex gap-3">
            <input
              ref="inputRef"
              v-model="inputMessage"
              type="text"
              placeholder="Message ApexAurum..."
              class="input flex-1"
              :disabled="chat.isStreaming"
            />
            <button
              type="submit"
              class="btn-primary px-6"
              :disabled="!inputMessage.trim() || chat.isStreaming"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            </button>
          </div>
          <p class="text-xs text-gray-500 mt-2 text-center">
            Agent: <span class="text-gold">{{ selectedAgent }}</span> |
            Press Enter to send
          </p>
        </form>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Bounce animation for typing indicator */
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
</style>
