import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { loginUser, registerUser, getDepartments } from '../api/auth'
import styles from '../styles/LoginPage.module.css'

export default function LoginPage({ onLogin }) {
  const { login } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [department, setDepartment] = useState('')
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const switchMode = async (next) => {
    setMode(next)
    setError(null)
    if (next === 'register' && departments.length === 0) {
      try {
        const list = await getDepartments()
        setDepartments(list)
        setDepartment(list[0] ?? '')
      } catch {
        // fallback: keep empty list, the select will show nothing
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (mode === 'login') {
        const data = await loginUser(email, password)
        login(data)
        onLogin()
      } else {
        await registerUser({ email, password, first_name: firstName, last_name: lastName, department })
        const data = await loginUser(email, password)
        login(data)
        onLogin()
      }
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || (mode === 'login' ? 'Login failed. Check your credentials.' : 'Registration failed.'))
    } finally {
      setLoading(false)
    }
  }

  const isLogin = mode === 'login'

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>OpenTeX</h1>
        <p className={styles.subtitle}>{isLogin ? 'Sign in to your account' : 'Create a new account'}</p>

        {error && <p className={styles.error}>{error}</p>}

        <form className={styles.form} onSubmit={handleSubmit}>
          {!isLogin && (
            <>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="firstName">First name</label>
                <input
                  id="firstName"
                  className={styles.input}
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="lastName">Last name</label>
                <input
                  id="lastName"
                  className={styles.input}
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
              <div className={styles.field}>
                <label className={styles.label} htmlFor="department">Department</label>
                <select
                  id="department"
                  className={styles.input}
                  required
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                >
                  {departments.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div className={styles.field}>
            <label className={styles.label} htmlFor="email">Email</label>
            <input
              id="email"
              className={styles.input}
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="password">Password</label>
            <input
              id="password"
              className={styles.input}
              type="password"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button className={styles.submitBtn} type="submit" disabled={loading}>
            {loading ? (isLogin ? 'Signing in...' : 'Registering...') : (isLogin ? 'Sign in' : 'Register')}
          </button>
        </form>

        <p className={styles.switchText}>
          {isLogin ? "Don't have an account?" : 'Already have an account?'}
          {' '}
          <button className={styles.switchBtn} onClick={() => switchMode(isLogin ? 'register' : 'login')}>
            {isLogin ? 'Register' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}