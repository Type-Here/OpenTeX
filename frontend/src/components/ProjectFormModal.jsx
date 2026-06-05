import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { createProject, updateProject } from '../api/projects'
import styles from '../styles/Modal.module.css'

export default function ProjectFormModal({ mode, project, onClose, onSaved }) {
  const { user } = useAuth()
  const [title, setTitle] = useState(project?.title ?? '')
  const [abstract, setAbstract] = useState(project?.abstract ?? '')
  const [tags, setTags] = useState(project?.tags?.join(', ') ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const parseTags = (raw) =>
    raw.split(',').map((t) => t.trim()).filter(Boolean)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      let result
      if (mode === 'create') {
        result = await createProject({
          title,
          abstract,
          tags: parseTags(tags),
          owner_id: user.user_id,
        })
      } else {
        result = await updateProject(project.id, {
          title,
          abstract,
          tags: parseTags(tags),
        })
      }
      onSaved(result)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to save project.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h2 className={styles.modalTitle}>
          {mode === 'create' ? 'New Project' : 'Edit Project'}
        </h2>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.label}>
            Title
            <input
              className={styles.input}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              autoFocus
            />
          </label>
          <label className={styles.label}>
            Abstract
            <textarea
              className={styles.textarea}
              value={abstract}
              onChange={(e) => setAbstract(e.target.value)}
              required
              rows={4}
            />
          </label>
          <label className={styles.label}>
            Tags <span className={styles.hint}>(comma-separated)</span>
            <input
              className={styles.input}
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. latex, math, physics"
            />
          </label>
          {error && <p className={styles.error}>{error}</p>}
          <div className={styles.btnRow}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className={styles.saveBtn} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
