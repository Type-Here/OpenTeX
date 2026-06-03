import { useState } from 'react'
import { useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ProjectDetailPage from './pages/ProjectDetailPage'

export default function App() {
  const { isAuthenticated } = useAuth()
  const [view, setView] = useState(() =>
    isAuthenticated ? { page: 'dashboard' } : { page: 'login' }
  )

  const navigate = (page, extra = {}) => setView({ page, ...extra })

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => navigate('dashboard')} />
  }

  if (view.page === 'detail') {
    return (
      <ProjectDetailPage
        projectId={view.projectId}
        onBack={() => navigate('dashboard')}
      />
    )
  }

  return (
    <DashboardPage
      onOpenProject={(id) => navigate('detail', { projectId: id })}
    />
  )
}
