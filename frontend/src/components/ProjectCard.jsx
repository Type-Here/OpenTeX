import styles from '../styles/ProjectCard.module.css'

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('it-IT')
}

export default function ProjectCard({ project, role, onClick }) {
  return (
    <button className={styles.card} onClick={onClick}>
      <div className={styles.top}>
        <span className={styles.title}>{project.title}</span>
        <span className={`${styles.badge} ${styles[role?.toLowerCase()]}`}>{role}</span>
      </div>
      {project.abstract && (
        <p className={styles.abstract}>{project.abstract}</p>
      )}
      {project.tags?.length > 0 && (
        <div className={styles.tags}>
          {project.tags.map((t) => <span key={t} className={styles.tag}>{t}</span>)}
        </div>
      )}
      <span className={styles.date}>{formatDate(project.created_at)}</span>
    </button>
  )
}
