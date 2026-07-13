import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { addDistribution, initialDraft, removeDistribution, replaceDraft, resetDraft, updateField, type DistributionType, type InteractionDraft } from './features/interaction/interactionSlice'
import { addMessage, setError, setLoading, setToolActivity } from './features/chat/chatSlice'
import { chat, getHcpProfile, getMaterialRecommendations, saveInteraction, type HcpProfile, type MaterialRecommendation } from './lib/api'
import type { RootState } from './store'

function normalizeDraft(draft: InteractionDraft): InteractionDraft {
  return {
    ...initialDraft, ...draft,
    hcp_name: draft?.hcp_name ?? '', interaction_type: draft?.interaction_type ?? '', occurred_at: draft?.occurred_at ?? '',
    topics: draft?.topics ?? '', notes: draft?.notes ?? '', channel: draft?.channel ?? '', outcome: draft?.outcome ?? '',
    sentiment: draft?.sentiment ?? 'neutral', follow_up_actions: draft?.follow_up_actions ?? '',
    attendees: Array.isArray(draft?.attendees) ? draft.attendees : [],
    distributions: Array.isArray(draft?.distributions) ? draft.distributions : [],
  }
}

function dateTimeParts(value: string | null) {
  if (!value) return { date: '', time: '' }
  const parsed = new Date(value)
  const local = Number.isNaN(parsed.getTime()) ? value : parsed.toISOString()
  return { date: local.slice(0, 10), time: local.slice(11, 16) }
}

function Field({ label, controlId, help, children }: { label: string; controlId?: string; help?: string; children: ReactNode }) {
  return <div className="field"><label htmlFor={controlId}>{label}</label>{children}{help ? <p className="field-help">{help}</p> : null}</div>
}

function App() {
  const dispatch = useDispatch()
  const draft = useSelector((state: RootState) => state.interaction)
  const chatState = useSelector((state: RootState) => state.chat)
  const [composer, setComposer] = useState('')
  const [profile, setProfile] = useState<HcpProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [recommendations, setRecommendations] = useState<MaterialRecommendation[]>([])
  const [recommendationLoading, setRecommendationLoading] = useState(false)
  const [recommendationError, setRecommendationError] = useState<string | null>(null)
  const [saveLoading, setSaveLoading] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState<number | null>(null)
  const [materialName, setMaterialName] = useState('')
  const [materialType, setMaterialType] = useState<DistributionType>('material')
  const [materialQuantity, setMaterialQuantity] = useState('1')
  const chatWindowRef = useRef<HTMLDivElement>(null)
  const dateParts = dateTimeParts(draft.occurred_at)
  const hasExtractedDetails = chatState.toolActivity.some((item) => item.tool_name === 'edit_interaction')

  useEffect(() => {
    const chatWindow = chatWindowRef.current
    if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight
  }, [chatState.messages, chatState.loading])

  function update<K extends keyof InteractionDraft>(field: K, value: InteractionDraft[K]) {
    dispatch(updateField({ field, value }))
    setSaveSuccess(null)
    setSaveError(null)
  }

  function updateDateTime(date: string, time: string) {
    update('occurred_at', date && time ? date + 'T' + time : date || time)
  }

  async function handleSend(event?: FormEvent) {
    event?.preventDefault()
    const message = composer.trim()
    if (!message || chatState.loading) return
    dispatch(addMessage({ id: 'rep-' + Date.now(), role: 'representative', content: message }))
    dispatch(setLoading(true))
    dispatch(setError(null))
    setComposer('')
    try {
      const result = await chat(message, draft)
      dispatch(replaceDraft(normalizeDraft(result.draft_patch)))
      const activity = result.tool_activity ?? []
      dispatch(setToolActivity(activity))
      dispatch(addMessage({ id: 'assistant-' + Date.now(), role: 'assistant', content: result.message }))
      const followUp = activity.find((item) => item.tool_name === 'create_follow_up')
      if (followUp) {
        dispatch(addMessage({ id: 'follow-up-' + Date.now(), role: 'assistant', content: 'Follow-up created: ' + followUp.summary }))
      }
    } catch (error) {
      dispatch(setError(error instanceof Error ? error.message : 'The assistant could not process that message.'))
    } finally {
      dispatch(setLoading(false))
    }
  }

  async function handleSave() {
    const missing = [!draft.hcp_name && 'HCP name', !draft.interaction_type && 'interaction type', !draft.occurred_at && 'date and time', !draft.channel && 'channel'].filter(Boolean)
    if (missing.length) {
      setSaveSuccess(null)
      setSaveError('Add the required ' + missing.join(', ') + ' before saving.')
      return
    }
    setSaveLoading(true)
    setSaveError(null)
    setSaveSuccess(null)
    try {
      const result = await saveInteraction(draft)
      setSaveSuccess(result.id)
      dispatch(resetDraft())
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'The interaction could not be saved.')
    } finally {
      setSaveLoading(false)
    }
  }

  async function handleLoadProfile() {
    const name = draft.hcp_name?.trim()
    if (!name) return
    setProfileLoading(true)
    setProfileError(null)
    try { setProfile(await getHcpProfile(name)) } catch (error) { setProfileError(error instanceof Error ? error.message : 'Could not load HCP context.') } finally { setProfileLoading(false) }
  }

  async function handleRecommendations() {
    const name = draft.hcp_name?.trim()
    const topic = draft.topics?.trim()
    if (!name || !topic) return
    setRecommendationLoading(true)
    setRecommendationError(null)
    try { setRecommendations(await getMaterialRecommendations(name, topic)) } catch (error) { setRecommendationError(error instanceof Error ? error.message : 'Could not load approved materials.') } finally { setRecommendationLoading(false) }
  }

  function addCustomDistribution() {
    const name = materialName.trim()
    const quantity = Number(materialQuantity)
    if (!name || !Number.isFinite(quantity) || quantity < 1) return
    dispatch(addDistribution({ material_name: name, distribution_type: materialType, quantity: Math.floor(quantity) }))
    setMaterialName('')
    setMaterialQuantity('1')
  }

  const materials = draft.distributions.filter((item) => item.distribution_type === 'material')
  const samples = draft.distributions.filter((item) => item.distribution_type === 'sample')
  const suggestedActions = (draft.follow_up_actions || '').split(/\n|;|(?<=\.)\s+/).map((item) => item.trim()).filter(Boolean)

  return <main className="reference-page">
    <header className="reference-header"><h1>Log HCP Interaction</h1></header>
    <div className="reference-grid">
      <section className="reference-form" aria-labelledby="details-title">
        <div className="reference-form-heading"><h2 id="details-title">Interaction Details</h2></div>
        <div className="reference-form-body">
          <div className="field-grid two-up">
            <Field label="HCP Name" controlId="hcp-name"><div className="field-with-action"><input id="hcp-name" value={draft.hcp_name ?? ''} onChange={(event) => update('hcp_name', event.target.value)} placeholder="Enter or select HCP..." /><button className="text-button" type="button" onClick={handleLoadProfile} disabled={!draft.hcp_name?.trim() || profileLoading}>{profileLoading ? 'Loading...' : 'Load profile'}</button></div></Field>
            <Field label="Interaction Type" controlId="interaction-type"><select id="interaction-type" value={draft.interaction_type ?? ''} onChange={(event) => update('interaction_type', event.target.value || null)}><option value="">Meeting</option><option value="meeting">Meeting</option><option value="call">Call</option><option value="email">Email</option><option value="lunch-and-learn">Lunch &amp; learn</option></select></Field>
            <Field label="Date" controlId="occurred-date"><input id="occurred-date" type="date" value={dateParts.date} onChange={(event) => updateDateTime(event.target.value, dateParts.time)} /></Field>
            <Field label="Time" controlId="occurred-time"><input id="occurred-time" type="time" value={dateParts.time} onChange={(event) => updateDateTime(dateParts.date, event.target.value)} /></Field>
          </div>
          {profile ? <p className="inline-context">Profile: {profile.name} ? {profile.specialty} ? {profile.organization} ? {profile.priority} priority</p> : null}
          {profileError ? <p className="inline-error" role="alert">{profileError}</p> : null}

          <Field label="Attendees" controlId="attendees"><input id="attendees" value={draft.attendees.join(', ')} onChange={(event) => update('attendees', event.target.value.split(',').map((item) => item.trim()).filter(Boolean))} placeholder="Enter names or search..." /></Field>
          <Field label="Topics Discussed" controlId="topics"><textarea id="topics" value={draft.topics ?? ''} onChange={(event) => update('topics', event.target.value)} placeholder="Enter key discussion points..." /></Field>
          <button className="voice-button" type="button" disabled>Summarize from Voice Note (Requires Consent)</button>

          <div className="distribution-section">
            <div className="section-line"><h3>Materials Shared / Samples Distributed</h3><button className="text-button" type="button" onClick={handleRecommendations} disabled={!draft.hcp_name?.trim() || !draft.topics?.trim() || recommendationLoading}>{recommendationLoading ? 'Searching...' : 'Search/Add'}</button></div>
            <div className="distribution-group"><h4>Materials Shared</h4>{materials.length ? materials.map((item) => <div className="distribution-item" key={item.material_name + item.quantity}><span>{item.material_name} ? Qty {item.quantity}</span><button className="remove-button" type="button" onClick={() => dispatch(removeDistribution(draft.distributions.indexOf(item)))}>Remove</button></div>) : <p className="empty-line">No materials added.</p>}</div>
            <div className="distribution-group"><h4>Samples Distributed</h4>{samples.length ? samples.map((item) => <div className="distribution-item" key={item.material_name + item.quantity}><span>{item.material_name} ? Qty {item.quantity}</span><button className="remove-button" type="button" onClick={() => dispatch(removeDistribution(draft.distributions.indexOf(item)))}>Remove</button></div>) : <p className="empty-line">No samples added.</p>}</div>
            <div className="distribution-adder"><input aria-label="Material or sample name" value={materialName} onChange={(event) => setMaterialName(event.target.value)} placeholder="Add approved material or sample..." /><select aria-label="Distribution type" value={materialType} onChange={(event) => setMaterialType(event.target.value as DistributionType)}><option value="material">Material</option><option value="sample">Sample</option></select><input aria-label="Quantity" type="number" min="1" value={materialQuantity} onChange={(event) => setMaterialQuantity(event.target.value)} /><button className="text-button" type="button" onClick={addCustomDistribution} disabled={!materialName.trim()}>Add</button></div>
            {recommendationError ? <p className="inline-error" role="alert">{recommendationError}</p> : null}
            {recommendations.length ? <div className="recommendation-list"><p>Approved recommendations</p>{recommendations.map((material) => <div className="recommendation-item" key={material.id}><span>{material.name}</span><button className="text-button" type="button" onClick={() => dispatch(addDistribution({ material_name: material.name, distribution_type: 'material', quantity: 1 }))}>Add</button></div>)}</div> : null}
          </div>

          <Field label="Observed/Inferred HCP Sentiment"><div className="radio-row" role="radiogroup" aria-label="Observed or inferred HCP sentiment">{(['positive', 'neutral', 'negative'] as const).map((sentiment) => <label key={sentiment}><input type="radio" name="sentiment" checked={draft.sentiment === sentiment} onChange={() => update('sentiment', sentiment)} /> {sentiment[0].toUpperCase() + sentiment.slice(1)}</label>)}</div></Field>
          <Field label="Outcomes" controlId="outcome"><textarea id="outcome" value={draft.outcome ?? ''} onChange={(event) => update('outcome', event.target.value)} placeholder="Key outcomes or agreements..." /></Field>
          <Field label="Follow-up Actions" controlId="follow-up-actions"><textarea id="follow-up-actions" value={draft.follow_up_actions ?? ''} onChange={(event) => update('follow_up_actions', event.target.value)} placeholder="Enter next steps or tasks..." /></Field>

          <div className="suggestions"><h3>AI Suggested Follow-up actions</h3>{suggestedActions.length ? <ul>{suggestedActions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No suggested actions yet.</p>}</div>
          <div className="save-row"><span aria-live="polite">{saveSuccess ? 'Interaction #' + saveSuccess + ' saved.' : saveError || 'Complete the required fields before saving.'}</span><button className="save-button" type="button" onClick={handleSave} disabled={saveLoading}>{saveLoading ? 'Saving...' : 'Save interaction'}</button></div>
        </div>
      </section>

      <aside className="assistant-card" aria-labelledby="assistant-title">
        <div className="assistant-card-heading"><h2 id="assistant-title">AI Assistant</h2><p>Log interaction via chat</p></div>
        <div className="assistant-body">
          <div className="chat-window" ref={chatWindowRef} aria-live="polite">{chatState.messages.map((message) => <div className={'chat-message is-' + message.role} key={message.id}><span className="message-role">{message.role === 'assistant' ? 'AI Assistant' : 'You'}</span><p>{message.content}</p></div>)}{chatState.loading ? <p className="chat-loading">Assistant is updating the form...</p> : null}</div>
          {chatState.toolActivity.length ? <div className="activity-line">Activity: {chatState.toolActivity.map((item) => item.tool_name).join(' ? ')}</div> : null}
          {hasExtractedDetails ? <div className="extracted-details">Extracted details here (review the form on the left).</div> : null}
          {chatState.error ? <p className="inline-error" role="alert">{chatState.error}</p> : null}
          <form className="chat-composer" onSubmit={handleSend}><label className="sr-only" htmlFor="chat-composer">Describe interaction</label><textarea id="chat-composer" value={composer} onChange={(event) => setComposer(event.target.value)} placeholder="Log interaction details here (e.g., ?Met Dr. Smith, discussed efficacy, provided brochure? or ask for help)." rows={3} disabled={chatState.loading} /><div className="composer-row"><span>Type ?Save this interaction? to log.</span><button className="log-button" type="submit" disabled={chatState.loading || !composer.trim()}>Log</button></div></form>
        </div>
      </aside>
    </div>
  </main>
}

export default App
