import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState, type KeyboardEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import { getAccessToken, supabase } from '../lib/supabaseClient'
import { getMessages, listConversations, streamChat, type Citation, type Message } from '../lib/api'

type Status = 'idle' | 'sending' | 'streaming' | 'error' | 'aborted'

export function ChatShell() {
  const queryClient = useQueryClient()
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loadedConversationId, setLoadedConversationId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [errorText, setErrorText] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)

  const conversationsQuery = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => listConversations(await getAccessToken()),
  })

  const messagesQuery = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: async () => getMessages(await getAccessToken(), conversationId as string),
    enabled: conversationId !== null,
  })

  // Adjust local state during render when the loaded conversation changes,
  // rather than in an effect (see https://react.dev/learn/you-might-not-need-an-effect).
  if (conversationId !== loadedConversationId && messagesQuery.data) {
    setLoadedConversationId(conversationId)
    setMessages(messagesQuery.data)
  }

  function startNewThread() {
    abortRef.current?.abort()
    setConversationId(null)
    setLoadedConversationId(null)
    setMessages([])
    setStatus('idle')
    setErrorText(null)
    composerRef.current?.focus()
  }

  async function send() {
    const text = draft.trim()
    if (!text || status === 'sending' || status === 'streaming') return

    const userMessage: Message = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
      citations: [],
    }
    const assistantId = `local-assistant-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: 'assistant', content: '', created_at: new Date().toISOString(), citations: [] },
    ])
    setDraft('')
    setStatus('sending')
    setErrorText(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const token = await getAccessToken()
      setStatus('streaming')
      await streamChat(
        token,
        { conversationId, message: text },
        {
          onToken: (chunk) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + chunk } : m)),
            )
          },
          onCitation: (citation: Citation) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, citations: [...m.citations, citation] } : m,
              ),
            )
          },
          onDone: (newConversationId) => {
            setStatus('idle')
            if (conversationId === null) setConversationId(newConversationId)
            queryClient.invalidateQueries({ queryKey: ['conversations'] })
          },
          onError: (message) => {
            setStatus('error')
            setErrorText(message)
          },
        },
        controller.signal,
      )
    } catch (err) {
      if (controller.signal.aborted) {
        setStatus('aborted')
      } else {
        setStatus('error')
        setErrorText(err instanceof Error ? err.message : 'Something went wrong')
      }
    } finally {
      composerRef.current?.focus()
    }
  }

  function stop() {
    abortRef.current?.abort()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  const busy = status === 'sending' || status === 'streaming'

  return (
    <div className="chat-shell">
      <aside className="sidebar">
        <button type="button" className="new-thread" onClick={startNewThread}>
          + New thread
        </button>
        <ul className="conversation-list">
          {conversationsQuery.data?.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={c.id === conversationId ? 'active' : ''}
                onClick={() => setConversationId(c.id)}
              >
                {c.title || 'Untitled'}
              </button>
            </li>
          ))}
        </ul>
        <button type="button" className="link-button" onClick={() => supabase.auth.signOut()}>
          Sign out
        </button>
      </aside>

      <main className="chat-main">
        <div className="message-list" aria-live="polite">
          {messages.map((m) => (
            <div key={m.id} className={`bubble ${m.role}`}>
              <ReactMarkdown>{m.content || (m.role === 'assistant' && busy ? '…' : '')}</ReactMarkdown>
              {m.citations.length > 0 && (
                <ul className="citations">
                  {m.citations.map((c) => (
                    <li key={c.index}>
                      [{c.index}] {c.title} v{c.version}
                      {c.section ? ` · ${c.section}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>

        {status === 'error' && errorText && <p className="error">{errorText}</p>}

        <div className="composer">
          <textarea
            ref={composerRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about an MHN policy…"
            disabled={busy}
            rows={2}
          />
          {busy ? (
            <button type="button" onClick={stop}>
              Stop
            </button>
          ) : (
            <button type="button" onClick={() => void send()} disabled={!draft.trim()}>
              Send
            </button>
          )}
        </div>
      </main>
    </div>
  )
}
