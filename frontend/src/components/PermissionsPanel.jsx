import { useEffect, useState } from 'react'
import { getUsers } from '../api/users'
import { listPermissions, assignPermission, revokePermission } from '../api/permissions'
import styles from '../styles/PermissionsPanel.module.css'

const ROLES = ['admin', 'editor', 'viewer']

export default function PermissionsPanel({ projectId, ownerId }) {
  const [permissions, setPermissions] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedUser, setSelectedUser] = useState('')
  const [selectedRole, setSelectedRole] = useState('editor')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const [perms, allUsers] = await Promise.all([
        listPermissions(projectId),
        getUsers(),
      ])
      setPermissions(perms)
      const permUserIds = new Set(perms.map((p) => p.user_id))
      setUsers(allUsers.filter((u) => u.id !== ownerId && !permUserIds.has(u.id)))
    } catch {
      setError('Failed to load permissions.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [projectId])

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!selectedUser) return
    setSaving(true)
    setSaveError(null)
    try {
      await assignPermission(projectId, { user_id: selectedUser, role: selectedRole })
      setSelectedUser('')
      await loadData()
    } catch (err) {
      setSaveError(err.response?.data?.detail ?? 'Failed to assign permission.')
    } finally {
      setSaving(false)
    }
  }

  const handleRevoke = async (userId) => {
    try {
      await revokePermission(projectId, userId)
      await loadData()
    } catch {
      setError('Failed to revoke permission.')
    }
  }

  const getUserName = (userId) => {
    const u = users.find((u) => u.id === userId)
    return u ? `${u.first_name} ${u.last_name}` : userId
  }

  return (
    <div className={styles.panel}>
      <h3 className={styles.panelTitle}>Collaborators</h3>

      {loading && <p className={styles.message}>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}

      {!loading && (
        <>
          {permissions.length === 0 ? (
            <p className={styles.empty}>No collaborators yet.</p>
          ) : (
            <ul className={styles.permList}>
              {permissions.map((perm) => (
                <li key={perm.id} className={styles.permRow}>
                  <span className={styles.permUser}>{perm.user_id}</span>
                  <span className={`${styles.roleBadge} ${styles[perm.role]}`}>{perm.role}</span>
                  <button
                    className={styles.revokeBtn}
                    onClick={() => handleRevoke(perm.user_id)}
                  >
                    Revoke
                  </button>
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={handleAdd} className={styles.addForm}>
            <h4 className={styles.addTitle}>Add collaborator</h4>
            <div className={styles.addRow}>
              <select
                className={styles.select}
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
              >
                <option value="">— Select user —</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.first_name} {u.last_name} ({u.department})
                  </option>
                ))}
              </select>
              <select
                className={styles.select}
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                ))}
              </select>
              <button type="submit" className={styles.addBtn} disabled={saving || !selectedUser}>
                {saving ? '…' : 'Add'}
              </button>
            </div>
            {saveError && <p className={styles.error}>{saveError}</p>}
          </form>
        </>
      )}
    </div>
  )
}
