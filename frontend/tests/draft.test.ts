import assert from 'node:assert/strict'
import test from 'node:test'
import * as draft from '../src/lib/draft.ts'

test('serializes blank controlled draft fields as null', () => {
  const result = draft.serializeDraft({
    hcp_name: '',
    interaction_type: '',
    occurred_at: '',
    attendees: [],
    topics: '',
    notes: '',
    distributions: [],
    channel: '',
    outcome: '',
    sentiment: 'neutral',
    follow_up_actions: '',
  })

  assert.equal(result.occurred_at, null)
  assert.equal(result.hcp_name, null)
  assert.deepEqual(result.attendees, [])
})
