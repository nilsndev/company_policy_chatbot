import { useState, type FormEvent } from 'react'
import { setProfile, type Department, type Role } from '../lib/api'
import { ProfileFields } from './ProfileFields'

interface CompleteProfileProps {
  token: string
  onSaved: () => void
}

export function CompleteProfile({ token, onSaved }: CompleteProfileProps) {
  const [department, setDepartment] = useState<Department | ''>('')
  const [role, setRole] = useState<Role | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!department || !role) return
    setBusy(true)
    setError(null)
    try {
      await setProfile(token, department, role)
      onSaved()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save profile')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <h1>Complete your profile</h1>
      <p>MHN scopes policy answers to your department and role.</p>
      <form className="auth-form" onSubmit={handleSubmit}>
        <ProfileFields
          department={department}
          role={role}
          onDepartmentChange={setDepartment}
          onRoleChange={setRole}
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy || !department || !role}>
          Continue
        </button>
      </form>
    </div>
  )
}
