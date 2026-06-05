import { useState } from 'react'
import { useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import StatsPage from './pages/StatsPage'
import BenchmarksPage from './pages/BenchmarksPage'

export default function App() {
  const { user, isAuthenticated } = useAuth()
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

  if (view.page === 'stats' && user?.is_admin) {
    return <StatsPage onBack={() => navigate('dashboard')} />
  }

  if (view.page === 'benchmarks' && user?.is_admin) {
    return <BenchmarksPage onBack={() => navigate('dashboard')} />
  }

  return (
    <DashboardPage
      onOpenProject={(id) => navigate('detail', { projectId: id })}
      onNavigate={(page) => navigate(page)}
    />
  )
}
