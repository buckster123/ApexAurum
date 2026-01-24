import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useChatStore = defineStore('chat', () => {
  // State
  const conversations = ref([])
  const currentConversation = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)
  const streamingContent = ref('')

  // Getters
  const sortedConversations = computed(() => {
    const convs = conversations.value || []
    if (!Array.isArray(convs)) return []
    return [...convs].sort((a, b) =>
      new Date(b.updated_at) - new Date(a.updated_at)
    )
  })

  // Actions
  async function fetchConversations() {
    try {
      const response = await api.get('/api/v1/chat/conversations')
      conversations.value = response.data.conversations || []
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
      conversations.value = []
    }
  }

  async function loadConversation(id) {
    try {
      const response = await api.get(`/api/v1/chat/conversations/${id}`)
      currentConversation.value = response.data
      messages.value = response.data.messages || []
    } catch (e) {
      console.error('Failed to load conversation:', e)
      currentConversation.value = null
      messages.value = []
    }
  }

  async function createConversation() {
    currentConversation.value = null
    messages.value = []
  }

  async function sendMessage(content, model = 'claude-sonnet-4-5-20250514') {
    // Add user message immediately
    messages.value.push({
      id: Date.now().toString(),
      role: 'user',
      content,
      created_at: new Date().toISOString()
    })

    // Start streaming
    isStreaming.value = true
    streamingContent.value = ''

    try {
      // For now, use non-streaming API (SSE requires different handling)
      const response = await api.post('/api/v1/chat/message', {
        message: content,
        conversation_id: currentConversation.value?.id,
        model,
        stream: false
      })

      // Add assistant message
      messages.value.push({
        id: Date.now().toString() + '-assistant',
        role: 'assistant',
        content: response.data.message,
        created_at: new Date().toISOString()
      })

      // Update conversation ID if new
      if (response.data.conversation_id && !currentConversation.value) {
        currentConversation.value = { id: response.data.conversation_id }
        await fetchConversations()
      }

    } catch (e) {
      // Add error message
      messages.value.push({
        id: Date.now().toString() + '-error',
        role: 'system',
        content: `Error: ${e.response?.data?.detail || e.message}`,
        created_at: new Date().toISOString()
      })
    } finally {
      isStreaming.value = false
      streamingContent.value = ''
    }
  }

  async function deleteConversation(id) {
    await api.delete(`/api/v1/chat/conversations/${id}`)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
      messages.value = []
    }
  }

  async function updateConversation(id, updates) {
    await api.patch(`/api/v1/chat/conversations/${id}`, updates)
    const conv = conversations.value.find(c => c.id === id)
    if (conv) {
      Object.assign(conv, updates)
    }
  }

  return {
    conversations,
    currentConversation,
    messages,
    isStreaming,
    streamingContent,
    sortedConversations,
    fetchConversations,
    loadConversation,
    createConversation,
    sendMessage,
    deleteConversation,
    updateConversation,
  }
})
