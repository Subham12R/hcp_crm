import type { InteractionDraft } from '../features/interaction/interactionSlice'
import type { ToolActivity } from '../features/chat/chatSlice'
import { serializeDraft } from './draft'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

export type ChatResponse = {
  message: string
  draft_patch: InteractionDraft
  tool_activity: ToolActivity[]
}

export type SavedInteraction = {
  id: number
  hcp_name: string
  occurred_at: string
  outcome: string | null
  created_at: string
}

export type HcpProfile = {
  name: string
  specialty: string
  organization: string
  priority: string
  interaction_history: Array<{
    occurred_at: string
    interaction_type: string
    outcome: string | null
  }>
}

export type MaterialRecommendation = {
  id: number
  name: string
  product: string
  material_type: string
  topic_tags: string[]
}

export type FollowUpPayload = {
  hcp_name: string
  due_on: string
  purpose: string
  next_action: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function chat(message: string, draft: InteractionDraft) {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, draft: serializeDraft(draft) }),
  })
}

export function saveInteraction(draft: InteractionDraft) {
  return request<SavedInteraction>('/interactions', {
    method: 'POST',
    body: JSON.stringify(serializeDraft(draft)),
  })
}

export function getHcpProfile(hcpName: string) {
  return request<HcpProfile>(`/hcps/${encodeURIComponent(hcpName)}`)
}

export function getMaterialRecommendations(hcpName: string, topic: string) {
  const params = new URLSearchParams({ hcp_name: hcpName, topic })
  return request<MaterialRecommendation[]>(`/materials?${params.toString()}`)
}

export function createFollowUp(payload: FollowUpPayload) {
  return request<{ id: number }>('/follow-ups', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
