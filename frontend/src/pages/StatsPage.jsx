import { useEffect, useState } from 'react'
import { getStats } from '../api/stats'
import styles from '../styles/StatsPage.module.css'

const DEPARTMENTS = ['Informatica', 'Fisica', 'Matematica', 'Chimica', 'Ingegneria', 'Biologia']

export default function StatsPage({ onBack }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [department, setDepartment] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    const params = {}
    if (department) params.department = department
    if (dateFrom) params.date_from = new Date(dateFrom).toISOString()
    if (dateTo) params.date_to = new Date(dateTo).toISOString()
    try {
      setData(await getStats(params))
    } catch {
      setError('Failed to load statistics.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const totals = data.reduce(
    (acc, row) => ({
      projects: acc.projects + row.project_count,
      collaborators: acc.collaborators + row.total_collaborators,
      activity: acc.activity + row.total_activity,
    }),
    { projects: 0, collaborators: 0, activity: 0 }
  )

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>← Back</button>
        <span className={styles.headerTitle}>Statistics — Projects by Department</span>
      </header>

      <main className={styles.main}>
        <section className={styles.description}>
          <p>
            Aggregation pipeline joining <strong>projects → users → permissions → activity_logs</strong> (4 collections via <code>$lookup</code>).
            Groups by owner department, sorted by total activity descending.
          </p>
        </section>

        <div className={styles.filters}>
          <label className={styles.filterLabel}>
            Department
            <select
              className={styles.select}
              value={department}
              onChange={e => setDepartment(e.target.value)}
            >
              <option value="">All departments</option>
              {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label className={styles.filterLabel}>
            From
            <input
              type="date"
              className={styles.input}
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
            />
          </label>
          <label className={styles.filterLabel}>
            To
            <input
              type="date"
              className={styles.input}
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
            />
          </label>
          <button className={styles.runBtn} onClick={load} disabled={loading}>
            {loading ? 'Loading…' : 'Apply filters'}
          </button>
        </div>

        {error && <p className={styles.error}>{error}</p>}

        {!loading && !error && (
          <>
            {data.length === 0 ? (
              <p className={styles.empty}>No results for these filters.</p>
            ) : (
              <>
                <div className={styles.summaryRow}>
                  <div className={styles.summaryCard}>
                    <span className={styles.summaryValue}>{data.length}</span>
                    <span className={styles.summaryLabel}>Departments</span>
                  </div>
                  <div className={styles.summaryCard}>
                    <span className={styles.summaryValue}>{totals.projects}</span>
                    <span className={styles.summaryLabel}>Total Projects</span>
                  </div>
                  <div className={styles.summaryCard}>
                    <span className={styles.summaryValue}>{totals.collaborators}</span>
                    <span className={styles.summaryLabel}>Total Collaborators</span>
                  </div>
                  <div className={styles.summaryCard}>
                    <span className={styles.summaryValue}>{totals.activity.toLocaleString()}</span>
                    <span className={styles.summaryLabel}>Total Activity Events</span>
                  </div>
                </div>

                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Department</th>
                        <th>Projects</th>
                        <th>Total Collaborators</th>
                        <th>Avg Collaborators</th>
                        <th>Total Activity</th>
                        <th>Activity bar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.map((row) => {
                        const maxActivity = data[0].total_activity
                        const pct = maxActivity ? (row.total_activity / maxActivity) * 100 : 0
                        return (
                          <tr key={row.department}>
                            <td><strong>{row.department}</strong></td>
                            <td className={styles.num}>{row.project_count}</td>
                            <td className={styles.num}>{row.total_collaborators}</td>
                            <td className={styles.num}>{row.avg_collaborators.toFixed(2)}</td>
                            <td className={styles.num}>{row.total_activity.toLocaleString()}</td>
                            <td className={styles.barCell}>
                              <div className={styles.bar} style={{ width: `${pct}%` }} />
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <p className={styles.note}>
                  Sorted by total activity descending. Pipeline: <code>$lookup</code> × 3, <code>$group</code>, <code>$sort</code>, <code>$project</code>.
                </p>
              </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
