import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getUsers } from '../api/users'
import styles from '../styles/LoginPage.module.css'

export default function LoginPage({ onLogin }) {
  const { login } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    getUsers()
      .then(setUsers)
      .catch(() => setError('Cannot load users. Make sure the backend is running.'))
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = (u) => {
    login({ user_id: u.id, first_name: u.first_name, last_name: u.last_name, email: u.email })
    onLogin()
  }

  const filtered = users.filter(
    (u) =>
      `${u.first_name} ${u.last_name} ${u.email} ${u.department}`
        .toLowerCase()
        .includes(search.toLowerCase())
  )

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>OpenTeX</h1>
        <p className={styles.subtitle}>Select your account to continue</p>

        {loading && <p className={styles.message}>Loading users…</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && !error && (
          <>
            <input
              className={styles.search}
              type="text"
              placeholder="Search by name, email or department…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {filtered.length === 0 ? (
              <p className={styles.message}>No users match your search.</p>
            ) : (
              <ul className={styles.list}>
                {filtered.map((u) => (
                  <li key={u.id}>
                    <button className={styles.userBtn} onClick={() => handleSelect(u)}>
                      <span className={styles.avatar}>
                        {u.first_name[0]}{u.last_name[0]}
                      </span>
                      <span className={styles.userInfo}>
                        <strong>{u.first_name} {u.last_name}</strong>
                        <span>{u.email}</span>
                        <span className={styles.dept}>{u.department}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  )
}
