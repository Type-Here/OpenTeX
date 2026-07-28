import { useState } from 'react'
import { runBenchmarks, runCompileBenchmark } from '../api/stats'
import styles from '../styles/BenchmarksPage.module.css'

const COMPILE_PHASES = [
  {
    label: 'Database query',
    desc: 'find({ project_id, file_type: tex | bib }) on files',
    msKey: 'db_ms',
    pctKey: 'db_pct',
  },
  {
    label: 'Filesystem write',
    desc: 'write sources into the isolated temp directory',
    msKey: 'io_ms',
    pctKey: 'io_pct',
  },
  {
    label: 'LaTeX compilation',
    desc: 'tectonic subprocess execution',
    msKey: 'tex_ms',
    pctKey: 'tex_pct',
  },
]

const QUERIES = [
  {
    label: 'Text search (title + abstract)',
    index: 'projects_text_search (Text Index)',
    withDesc: '$text: { $search: "latex" }',
    withoutDesc: '$regex on title + abstract (COLLSCAN)',
  },
  {
    label: 'Compound: owner_id + created_at sort',
    index: 'projects_owner_date (Compound Index)',
    withDesc: 'count_documents({ owner_id })',
    withoutDesc: 'same query, no compound index',
  },
  {
    label: 'Permissions by project_id',
    index: 'permissions_project_id (Single field)',
    withDesc: 'count_documents({ project_id })',
    withoutDesc: 'same query, no index',
  },
  {
    label: 'Activity logs by project_id',
    index: 'activity_logs_project_id (Single field)',
    withDesc: 'count_documents({ project_id })',
    withoutDesc: 'same query, no index — ~30k docs',
  },
  {
    label: 'Files by project_id',
    index: 'files_project_id (Single field)',
    withDesc: 'count_documents({ project_id })',
    withoutDesc: 'same query, no index',
  },
]

function SpeedupBadge({ value }) {
  const color = value >= 5 ? '#065f46' : value >= 2 ? '#92400e' : '#374151'
  const bg    = value >= 5 ? '#d1fae5' : value >= 2 ? '#fef3c7' : '#f3f4f6'
  return (
    <span className={styles.speedupBadge} style={{ color, background: bg }}>
      {value}x
    </span>
  )
}

export default function BenchmarksPage({ onBack }) {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Compilation-phase benchmark — independent state from the index benchmark
  const [compile, setCompile] = useState(null)
  const [compileLoading, setCompileLoading] = useState(false)
  const [compileError, setCompileError] = useState(null)

  const handleRunCompile = async () => {
    setCompileLoading(true)
    setCompileError(null)
    setCompile(null)
    try {
      setCompile(await runCompileBenchmark())
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Compilation benchmark failed. Is the backend running?'
      setCompileError(msg)
    } finally {
      setCompileLoading(false)
    }
  }

  const handleRun = async () => {
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      setResults(await runBenchmarks())
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Benchmark failed. Is the backend running?'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const merged = QUERIES.map((q, i) => ({
    ...q,
    ...(results ? results[i] : {}),
  }))

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>← Back</button>
        <span className={styles.headerTitle}>Benchmark — Indexes (Issue #8 / #9)</span>
      </header>

      <main className={styles.main}>
        <h2 className={styles.sectionTitleFirst}>Benchmark — Indexes</h2>

        <section className={styles.description}>
          <p>
            Each query is run <strong>N = 10 times</strong> with the index active, then the index is
            temporarily dropped and the query is run again 10 times, then the index is recreated.
            The reported value is the average elapsed time in milliseconds.
          </p>
          <p className={styles.descNote}>
            Text search "without index" uses a case-insensitive regex (semantically equivalent, forces COLLSCAN).
          </p>
        </section>

        <div className={styles.runRow}>
          <button className={styles.runBtn} onClick={handleRun} disabled={loading}>
            {loading ? 'Running benchmark…' : '▶  Run Benchmark  (N = 10)'}
          </button>
          {loading && (
            <span className={styles.runHint}>
              This takes ~5–15 s — indexes are dropped and recreated for each query.
            </span>
          )}
        </div>

        {error && <p className={styles.error}>{error}</p>}

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Query</th>
                <th>Index used</th>
                <th className={styles.numHead}>With index (ms)</th>
                <th className={styles.numHead}>Without index (ms)</th>
                <th className={styles.numHead}>Speedup</th>
              </tr>
            </thead>
            <tbody>
              {merged.map((row, i) => (
                <tr key={i}>
                  <td>
                    <div className={styles.queryLabel}>{row.label}</div>
                    <div className={styles.queryWith}><code>{row.withDesc}</code></div>
                    <div className={styles.queryWithout}><code>{row.withoutDesc}</code></div>
                  </td>
                  <td className={styles.indexCell}>{row.index}</td>
                  <td className={styles.num}>
                    {row.with_ms !== undefined ? row.with_ms.toFixed(3) : <span className={styles.dash}>—</span>}
                  </td>
                  <td className={styles.num}>
                    {row.without_ms !== undefined ? row.without_ms.toFixed(3) : <span className={styles.dash}>—</span>}
                  </td>
                  <td className={styles.num}>
                    {row.speedup !== undefined ? <SpeedupBadge value={row.speedup} /> : <span className={styles.dash}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {results && (
          <p className={styles.note}>
            N = 10 runs per query, averaged. 1 warmup run excluded from timing.
          </p>
        )}

        <h2 className={styles.sectionTitle}>Benchmark — Compilation phases</h2>

        <section className={styles.description}>
          <p>
            Splits <code>POST /projects/&#123;id&#125;/compile</code> into its three phases —
            <strong> database query</strong>, <strong>filesystem write</strong> and
            <strong> LaTeX compilation</strong> — measured with <code>time.perf_counter()</code>.
            The reported value is the mean over <strong>5 measured runs</strong>, with one warm-up
            run excluded because Tectonic caches packages on first use.
          </p>
          <p className={styles.descNote}>
            The benchmark always compiles the same fixed document (the seeded "Compilation
            Benchmark" project), so results are comparable across runs.
          </p>
        </section>

        <div className={styles.runRow}>
          <button className={styles.runBtn} onClick={handleRunCompile} disabled={compileLoading}>
            {compileLoading ? 'Running compilations…' : '▶  Run Compilation Benchmark'}
          </button>
          <span className={styles.runHint}>
            Runs real LaTeX compilations — takes roughly 30–60 s.
          </span>
        </div>

        {compileError && <p className={styles.error}>{compileError}</p>}

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Phase</th>
                <th className={styles.numHead}>Mean (ms)</th>
                <th className={styles.numHead}>% of total</th>
              </tr>
            </thead>
            <tbody>
              {COMPILE_PHASES.map((phase) => (
                <tr key={phase.label}>
                  <td>
                    <div className={styles.queryLabel}>{phase.label}</div>
                    <div className={styles.queryWith}><code>{phase.desc}</code></div>
                  </td>
                  <td className={styles.num}>
                    {compile ? compile[phase.msKey].toFixed(3) : <span className={styles.dash}>—</span>}
                  </td>
                  <td className={styles.num}>
                    {compile ? `${compile[phase.pctKey].toFixed(2)} %` : <span className={styles.dash}>—</span>}
                  </td>
                </tr>
              ))}
              <tr className={styles.totalRow}>
                <td><div className={styles.queryLabel}>Total</div></td>
                <td className={styles.num}>
                  {compile ? compile.total_ms.toFixed(3) : <span className={styles.dash}>—</span>}
                </td>
                <td className={styles.num}>
                  {compile ? '100.00 %' : <span className={styles.dash}>—</span>}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {compile && (
          <p className={styles.note}>
            {compile.runs} measured runs on project "{compile.project_title}", 1 warm-up run
            excluded. The database phase is expected to be a fraction of a percent of the total:
            the bottleneck is the external LaTeX compiler, not the data layer.
          </p>
        )}
      </main>
    </div>
  )
}
