import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export type ChatMessage = {
  id: string
  role: 'representative' | 'assistant'
  content: string
}

export type ToolActivity = {
  tool_name: string
  summary: string
}

type ChatState = {
  messages: ChatMessage[]
  loading: boolean
  toolActivity: ToolActivity[]
  error: string | null
}

const initialState: ChatState = {
  messages: [
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Tell me what happened in the interaction. I’ll extract the details and keep the draft ready for your review.',
    },
  ],
  loading: false,
  toolActivity: [],
  error: null,
}

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload)
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload
    },
    setToolActivity: (state, action: PayloadAction<ToolActivity[]>) => {
      state.toolActivity = action.payload
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
  },
})

export const { addMessage, setLoading, setToolActivity, setError } = chatSlice.actions

export default chatSlice.reducer
