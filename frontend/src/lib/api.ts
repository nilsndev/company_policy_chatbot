export const DEPARTMENTS = [
  'Clinical',
  'IT & Security',
  'HR',
  'Compliance & Risk',
  'Finance',
  'Facilities & Operations',
] as const
export type Department = (typeof DEPARTMENTS)[number]

export const ROLES = ['staff', 'manager', 'director', 'compliance_officer'] as const
export type Role = (typeof ROLES)[number]

export interface Profile {
  id: string
  department: Department | null
  role: Role | null
}

export interface Conversation {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface Citation {
  index: number
  policy_id: string
  title: string
  version: number
  section: string | null
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  citations: Citation[]
}

async function apiFetch(path: string, token: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      ...init.headers,
      Authorization: `Bearer ${token}`,
    },
  })
  if (!response.ok) {
    throw new Error(`${init.method ?? 'GET'} ${path} failed: ${response.status}`)
  }
  return response
}

export async function getProfile(token: string): Promise<Profile> {
  const response = await apiFetch('/profile', token)
  return response.json()
}

export async function setProfile(token: string, department: Department, role: Role): Promise<Profile> {
  const response = await apiFetch('/profile', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ department, role }),
  })
  return response.json()
}

export async function listConversations(token: string): Promise<Conversation[]> {
  const response = await apiFetch('/conversations', token)
  return response.json()
}

export async function getMessages(token: string, conversationId: string): Promise<Message[]> {
  const response = await apiFetch(`/conversations/${conversationId}/messages`, token)
  return response.json()
}

export interface ChatStreamHandlers {
  onToken: (text: string) => void
  onCitation: (citation: Citation) => void
  onDone: (conversationId: string) => void
  onError: (message: string) => void
}

/**
 * Streams a chat reply over SSE. Uses fetch (not EventSource) because it's a POST
 * with a bearer token and JSON body; frames are parsed manually.
 */
export async function streamChat(
  token: string,
  body: { conversationId: string | null; message: string },
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ conversation_id: body.conversationId, message: body.message }),
  })

  if (!response.ok || !response.body) {
    handlers.onError(`chat request failed: ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      const eventLine = frame.split('\n').find((line) => line.startsWith('event: '))
      const dataLine = frame.split('\n').find((line) => line.startsWith('data: '))
      if (!eventLine || !dataLine) continue

      const event = eventLine.slice('event: '.length)
      const data = JSON.parse(dataLine.slice('data: '.length))

      if (event === 'token') handlers.onToken(data.text)
      else if (event === 'citation') handlers.onCitation(data as Citation)
      else if (event === 'done') handlers.onDone(data.conversation_id)
      else if (event === 'error') handlers.onError(data.message)
    }
  }
}
