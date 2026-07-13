import type { InteractionDraft } from '../features/interaction/interactionSlice'

function nullIfBlank(value: string | null) {
  return value?.trim() ? value : null
}

export function serializeDraft(draft: InteractionDraft): InteractionDraft {
  return {
    ...draft,
    hcp_name: nullIfBlank(draft.hcp_name),
    interaction_type: nullIfBlank(draft.interaction_type),
    occurred_at: nullIfBlank(draft.occurred_at),
    topics: nullIfBlank(draft.topics),
    notes: nullIfBlank(draft.notes),
    channel: nullIfBlank(draft.channel),
    outcome: nullIfBlank(draft.outcome),
    follow_up_actions: nullIfBlank(draft.follow_up_actions),
  }
}
