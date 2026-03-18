import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import GamesPage from './pages/GamesPage'
import RankingsPage from './pages/RankingsPage'
import LoginPage from './pages/LoginPage'
import PendingPicksPage from './pages/admin/PendingPicksPage'
import PickHistoryPage from './pages/admin/PickHistoryPage'
import PublicPicksPage from './pages/PublicPicksPage'
import CLVDashboard from './pages/CLVDashboard'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0a0a0a] text-white">
        <Navbar />
        <main className="pt-16">
          <Routes>
            <Route path="/"       element={<Navigate to="/games" replace />} />
            <Route path="/games"  element={<GamesPage />} />
            <Route path="/rankings" element={<RankingsPage />} />
            <Route path="/picks"    element={<PublicPicksPage />} />
            <Route path="/clv"      element={<CLVDashboard />} />
            <Route path="/login"  element={<LoginPage />} />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <PendingPicksPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/history"
              element={
                <ProtectedRoute>
                  <PickHistoryPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
