import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { listProjects } from '../api/projects'
import ProjectCard from '../components/ProjectCard'
import ProjectFormModal from '../components/ProjectFormModal'
import styles from '../styles/DashboardPage.module.css'

export default function DashboardPage({ onOpenProject, onNavigate }) {
  const { user, logout } = useAuth()
  const [myProjects, setMyProjects] = useState([])
  const [sharedProjects, setSharedProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [search, setSearch] = useState('')
  const [activeSearch, setActiveSearch] = useState('')

  const loadProjects = async (q = activeSearch) => {
    setSearching(true)
    setError(null)
    try {
      const params = q ? { q } : {}
      const [owned, shared] = await Promise.all([
        listProjects({ owner_id: user.id, ...params }),
        listProjects({ member_id: user.id, ...params }),
      ])
      setMyProjects(owned)
      setSharedProjects(shared)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load projects.')
    } finally {
      setSearching(false)
      setLoading(false)
    }
  }

  // Debounce typing so each keystroke does not hit the API.
  useEffect(() => {
    const timer = setTimeout(() => setActiveSearch(search.trim()), 300)
    return () => clearTimeout(timer)
  }, [search])

  // Also covers the initial load, when activeSearch is still empty.
  useEffect(() => { loadProjects(activeSearch) }, [activeSearch])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.logo}>OpenTeX</span>
        {user.is_admin && (
          <nav className={styles.nav}>
            <button className={styles.navBtn} onClick={() => onNavigate('stats')}>Statistics</button>
            <button className={styles.navBtn} onClick={() => onNavigate('benchmarks')}>Benchmarks</button>
          </nav>
        )}
        <div className={styles.userMeta}>
          <span>{user.first_name} {user.last_name}</span>
          <button className={styles.logoutBtn} onClick={logout}>Log out</button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.sectionHeader}>
          <h2>My Projects</h2>
          <button className={styles.newBtn} onClick={() => setShowCreate(true)}>
            + New Project
          </button>
        </div>

        <div className={styles.searchRow}>
          <input
            className={styles.searchInput}
            type="search"
            value={search}
            placeholder="Search projects by title or abstract…"
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className={styles.clearBtn} onClick={() => setSearch('')}>
              Clear
            </button>
          )}
          <span className={styles.searchHint}>
            {searching && !loading
              ? 'Searching…'
              : 'MongoDB full-text index on title + abstract — matches whole words'}
          </span>
        </div>

        {loading && <p className={styles.message}>Loading…</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && !error && (
          <>
            {myProjects.length === 0 ? (
              <p className={styles.empty}>
                {activeSearch
                  ? `No projects of yours match “${activeSearch}”.`
                  : 'No projects yet. Create your first one!'}
              </p>
            ) : (
              <div className={styles.grid}>
                {myProjects.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={p}
                    role="Owner"
                    onClick={() => onOpenProject(p.id)}
                  />
                ))}
              </div>
            )}

            {sharedProjects.length > 0 && (
              <>
                <h2 className={styles.sectionTitle}>Shared with me</h2>
                <div className={styles.grid}>
                  {sharedProjects.map((p) => (
                    <ProjectCard
                      key={p.id}
                      project={p}
                      role="Collaborator"
                      onClick={() => onOpenProject(p.id)}
                    />
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </main>

      {showCreate && (
        <ProjectFormModal
          mode="create"
          onClose={() => setShowCreate(false)}
          onSaved={() => { setShowCreate(false); setSearch(''); loadProjects('') }}
        />
      )}
    </div>
  )
}
