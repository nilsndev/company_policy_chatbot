import { DEPARTMENTS, ROLES, type Department, type Role } from '../lib/api'

interface ProfileFieldsProps {
  department: Department | ''
  role: Role | ''
  onDepartmentChange: (value: Department) => void
  onRoleChange: (value: Role) => void
}

export function ProfileFields({ department, role, onDepartmentChange, onRoleChange }: ProfileFieldsProps) {
  return (
    <>
      <label className="field">
        <span>Department</span>
        <select
          required
          value={department}
          onChange={(e) => onDepartmentChange(e.target.value as Department)}
        >
          <option value="" disabled>
            Select department
          </option>
          {DEPARTMENTS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Role</span>
        <select required value={role} onChange={(e) => onRoleChange(e.target.value as Role)}>
          <option value="" disabled>
            Select role
          </option>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>
    </>
  )
}
