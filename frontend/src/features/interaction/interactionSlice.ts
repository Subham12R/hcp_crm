import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

export type DistributionType = 'material' | 'sample'

export type Distribution = {
  material_name: string
  distribution_type: DistributionType
  quantity: number
}

export type InteractionDraft = {
  hcp_name: string | null
  interaction_type: string | null
  occurred_at: string | null
  attendees: string[]
  topics: string | null
  notes: string | null
  distributions: Distribution[]
  channel: string | null
  outcome: string | null
  sentiment: 'positive' | 'neutral' | 'negative' | null
  follow_up_actions: string | null
}

export const initialDraft: InteractionDraft = {
  hcp_name: null,
  interaction_type: null,
  occurred_at: null,
  attendees: [],
  topics: null,
  notes: null,
  distributions: [],
  channel: null,
  outcome: null,
  sentiment: 'neutral',
  follow_up_actions: null,
}

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: initialDraft,
  reducers: {
    updateField: <K extends keyof InteractionDraft>(
      state: InteractionDraft,
      action: PayloadAction<{ field: K; value: InteractionDraft[K] }>,
    ) => {
      state[action.payload.field] = action.payload.value
    },
    replaceDraft: (_, action: PayloadAction<InteractionDraft>) => action.payload,
    addDistribution: (state, action: PayloadAction<Distribution>) => {
      state.distributions.push(action.payload)
    },
    removeDistribution: (state, action: PayloadAction<number>) => {
      state.distributions.splice(action.payload, 1)
    },
    resetDraft: () => initialDraft,
  },
})

export const {
  updateField,
  replaceDraft,
  addDistribution,
  removeDistribution,
  resetDraft,
} = interactionSlice.actions

export default interactionSlice.reducer
