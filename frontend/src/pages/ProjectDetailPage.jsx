import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getProject, deleteProject } from '../api/projects'
import ProjectFormModal from '../components/ProjectFormModal'
import ConfirmDialog from '../components/ConfirmDialog'
import PermissionsPanel from '../components/PermissionsPanel'
import styles from '../styles/ProjectDetailPage.module.css'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('it-IT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}

export default function ProjectDetailPage({ projectId, onBack }) {
  const { user } = useAuth()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadProject = () => {
    setLoading(true)
    getProject(projectId)
      .then(setProject)
      .catch((e) => {
        if (e.response?.status === 403) setError('Access denied: insufficient permissions.')
        else setError('Project not found.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadProject() }, [projectId])

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteProject(projectId)
      onBack()
    } catch {
      setError('Failed to delete project.')
      setDeleting(false)
      setShowDelete(false)
    }
  }

  const isOwner = project && project.owner_id === user.user_id

  if (loading) return <div className={styles.page}><p className={styles.message}>Loading…</p></div>
  if (error) return (
    <div className={styles.page}>
      <p className={styles.error}>{error}</p>
      <button className={styles.backBtn} onClick={onBack}>← Back to Dashboard</button>
    </div>
  )

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>← Back</button>
        <div className={styles.actions}>
          {isOwner && (
            <>
              <button className={styles.editBtn} onClick={() => setShowEdit(true)}>Edit</button>
              <button className={styles.deleteBtn} onClick={() => setShowDelete(true)}>Delete</button>
            </>
          )}
        </div>
      </header>

      <main className={styles.main}>
        <h1 className={styles.title}>{project.title}</h1>
        <p className={styles.abstract}>{project.abstract}</p>

        {project.tags.length > 0 && (
          <div className={styles.tags}>
            {project.tags.map((t) => <span key={t} className={styles.tag}>{t}</span>)}
          </div>
        )}

        <div className={styles.meta}>
          <span>Created: {formatDate(project.created_at)}</span>
          {project.updated_at && <span>Updated: {formatDate(project.updated_at)}</span>}
          {isOwner && <span className={styles.ownerBadge}>You are the owner</span>}
        </div>

        {isOwner && (
          <PermissionsPanel projectId={projectId} ownerId={user.user_id} />
        )}
      </main>

      {showEdit && (
        <ProjectFormModal
          mode="edit"
          project={project}
          onClose={() => setShowEdit(false)}
          onSaved={(updated) => { setProject(updated); setShowEdit(false) }}
        />
      )}

      {showDelete && (
        <ConfirmDialog
          message={`Delete "${project.title}"? This action cannot be undone.`}
          confirmLabel={deleting ? 'Deleting…' : 'Delete'}
          onConfirm={handleDelete}
          onCancel={() => setShowDelete(false)}
        />
      )}
    </div>
  )
}
