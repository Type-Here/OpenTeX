import { useEffect, useRef, useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { latex } from 'codemirror-lang-latex'
import { listProjectFiles, updateFileContent, createProjectFile, deleteFile, compileProject } from '../api/files'
import styles from '../styles/EditorPage.module.css'

const EDITABLE_TYPES = ['tex', 'bib']

function pickInitialFile(files) {
  const editable = files.filter(f => EDITABLE_TYPES.includes(f.file_type))
  if (!editable.length) return null
  const main = editable.find(f => f.filename === 'main.tex')
  return main ?? editable.sort((a, b) => a.filename.localeCompare(b.filename))[0]
}

export default function EditorPage({ projectId, projectTitle, onBack }) {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [content, setContent] = useState('')
  const [dirty, setDirty] = useState(false)
  const [loadingFiles, setLoadingFiles] = useState(true)
  const [filesError, setFilesError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)
  const [compiling, setCompiling] = useState(false)
  const [compileError, setCompileError] = useState(null)
  const [showNewFile, setShowNewFile] = useState(false)
  const [newFilename, setNewFilename] = useState('')
  const [newFileType, setNewFileType] = useState('tex')
  const [creatingFile, setCreatingFile] = useState(false)
  const [createError, setCreateError] = useState(null)
  const saveTimeoutRef = useRef(null)

  useEffect(() => {
    setLoadingFiles(true)
    setFilesError(null)
    listProjectFiles(projectId)
      .then(fetched => {
        setFiles(fetched)
        const initial = pickInitialFile(fetched)
        setSelectedFile(initial)
        setContent(initial?.content ?? '')
        setDirty(false)
      })
      .catch(() => setFilesError('Failed to load project files.'))
      .finally(() => setLoadingFiles(false))
  }, [projectId])

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (selectedFile && dirty && !saving) handleSave()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [selectedFile, dirty, saving, content])

  const showSaveResult = (result) => {
    setSaveResult(result)
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    saveTimeoutRef.current = setTimeout(() => setSaveResult(null), 4000)
  }

  const handleSave = async () => {
    if (!selectedFile) return
    setSaving(true)
    try {
      await updateFileContent(selectedFile.id, content)
      setFiles(prev => prev.map(f =>
        f.id === selectedFile.id ? { ...f, content } : f
      ))
      setSelectedFile(prev => ({ ...prev, content }))
      setDirty(false)
      showSaveResult({ ok: true, msg: 'Saved' })
    } catch (err) {
      showSaveResult({ ok: false, msg: err.response?.data?.detail ?? 'Save failed' })
    } finally {
      setSaving(false)
    }
  }

  const handleSelectFile = (file) => {
    if (!EDITABLE_TYPES.includes(file.file_type)) return
    if (file.id === selectedFile?.id) return
    if (dirty && !window.confirm('You have unsaved changes. Switch file anyway?')) return
    setSelectedFile(file)
    setContent(file.content ?? '')
    setDirty(false)
    setCompileError(null)
  }

  const handleCompile = async () => {
    setCompiling(true)
    setCompileError(null)
    const response = await compileProject(projectId)
    if (response.status === 200) {
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${projectTitle}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } else {
      try {
        const text = new TextDecoder().decode(response.data)
        const body = JSON.parse(text)
        setCompileError(body.log ?? body.error ?? body.detail ?? `Error ${response.status}`)
      } catch {
        setCompileError(`Server error ${response.status}`)
      }
    }
    setCompiling(false)
  }

  const handleDeleteFile = async (file) => {
    if (!window.confirm(`Delete "${file.filename}"? This cannot be undone.`)) return
    try {
      await deleteFile(file.id)
      const remaining = files.filter(f => f.id !== file.id)
      setFiles(remaining)
      if (selectedFile?.id === file.id) {
        const next = pickInitialFile(remaining)
        setSelectedFile(next)
        setContent(next?.content ?? '')
        setDirty(false)
      }
    } catch {
      // silently ignore — file might already be gone
    }
  }

  const handleCreateFile = async (e) => {
    e.preventDefault()
    const name = newFilename.trim()
    if (!name) return
    setCreatingFile(true)
    setCreateError(null)
    try {
      const created = await createProjectFile(projectId, name, newFileType)
      setFiles(prev => [...prev, created])
      setSelectedFile(created)
      setContent(created.content ?? '')
      setDirty(false)
      setShowNewFile(false)
      setNewFilename('')
      setNewFileType('tex')
    } catch (err) {
      const detail = err.response?.data?.detail
      setCreateError(typeof detail === 'string' ? detail : 'Failed to create file.')
    } finally {
      setCreatingFile(false)
    }
  }

  const handleContentChange = (val) => {
    setContent(val)
    setDirty(val !== (selectedFile?.content ?? ''))
  }

  if (loadingFiles) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <button className={styles.backBtn} onClick={onBack}>← Back</button>
          <span className={styles.headerTitle}>{projectTitle}</span>
        </header>
        <p className={styles.loadingMsg}>Loading files…</p>
      </div>
    )
  }

  if (filesError) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <button className={styles.backBtn} onClick={onBack}>← Back</button>
          <span className={styles.headerTitle}>{projectTitle}</span>
        </header>
        <p className={styles.errorMsg}>{filesError}</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>← Back</button>
        <span className={styles.headerTitle}>{projectTitle}</span>
        <button
          className={`${styles.saveBtn}${dirty ? ` ${styles.dirty}` : ''}`}
          onClick={handleSave}
          disabled={saving || !selectedFile || !dirty}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          className={styles.compileBtn}
          onClick={handleCompile}
          disabled={compiling}
        >
          {compiling ? 'Compiling…' : 'Compile'}
        </button>
      </header>

      <div className={styles.body}>
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <span className={styles.sidebarTitle}>Files</span>
            <button
              className={styles.newFileBtn}
              onClick={() => { setShowNewFile(v => !v); setCreateError(null) }}
              title="New file"
            >+</button>
          </div>

          {showNewFile && (
            <form className={styles.newFileForm} onSubmit={handleCreateFile}>
              <input
                className={styles.newFileInput}
                value={newFilename}
                onChange={e => setNewFilename(e.target.value)}
                placeholder="filename.tex"
                autoFocus
              />
              <select
                className={styles.newFileSelect}
                value={newFileType}
                onChange={e => setNewFileType(e.target.value)}
              >
                <option value="tex">.tex</option>
                <option value="bib">.bib</option>
              </select>
              <button className={styles.newFileSubmit} type="submit" disabled={creatingFile || !newFilename.trim()}>
                {creatingFile ? '…' : 'Create'}
              </button>
              {createError && <p className={styles.createError}>{createError}</p>}
            </form>
          )}

          {files.length === 0 && !showNewFile && (
            <p className={styles.sidebarEmpty}>No files in this project.</p>
          )}
          {files.map(file => {
            const editable = EDITABLE_TYPES.includes(file.file_type)
            const active = file.id === selectedFile?.id
            return (
              <div
                key={file.id}
                className={[
                  styles.fileItem,
                  active ? styles.active : '',
                  !editable ? styles.disabled : '',
                ].join(' ')}
                onClick={() => editable && handleSelectFile(file)}
                title={editable ? file.filename : `${file.filename} (not editable)`}
              >
                <span className={styles.fileName}>{file.filename}</span>
                <span className={styles.fileType}>{file.file_type}</span>
                <button
                  className={styles.deleteFileBtn}
                  onClick={e => { e.stopPropagation(); handleDeleteFile(file) }}
                  title={`Delete ${file.filename}`}
                >−</button>
              </div>
            )
          })}
        </aside>

        <div className={styles.editorArea}>
          {!selectedFile ? (
            <div className={styles.editorPlaceholder}>
              {files.some(f => EDITABLE_TYPES.includes(f.file_type))
                ? 'Select a .tex or .bib file from the sidebar'
                : 'No editable files in this project'}
            </div>
          ) : (
            <CodeMirror
              value={content}
              extensions={[latex()]}
              onChange={handleContentChange}
              style={{ flex: 1, fontSize: '14px', overflow: 'auto' }}
              height="100%"
            />
          )}

          {compileError && (
            <div className={styles.compileErrorPanel}>
              <div className={styles.compileErrorHeader}>
                <span>Compile Error</span>
                <button className={styles.dismissBtn} onClick={() => setCompileError(null)}>✕</button>
              </div>
              <pre className={styles.compileErrorLog}>{compileError}</pre>
            </div>
          )}
        </div>
      </div>

      <div className={styles.statusBar}>
        {saveResult && (
          <span className={saveResult.ok ? styles.statusOk : styles.statusErr}>
            {saveResult.msg}
          </span>
        )}
        {!saveResult && selectedFile && dirty && (
          <span className={styles.statusDirty}>Unsaved changes</span>
        )}
        {!saveResult && selectedFile && !dirty && (
          <span>{selectedFile.filename}</span>
        )}
      </div>
    </div>
  )
}
