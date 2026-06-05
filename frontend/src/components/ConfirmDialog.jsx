import styles from '../styles/Modal.module.css'

export default function ConfirmDialog({ message, confirmLabel = 'Confirm', onConfirm, onCancel }) {
  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <p className={styles.confirmMsg}>{message}</p>
        <div className={styles.btnRow}>
          <button className={styles.cancelBtn} onClick={onCancel}>Cancel</button>
          <button className={styles.deleteBtn} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
