import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import SchedulePage from './pages/SchedulePage'
import RankingsPage from './pages/RankingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0a0a0a] text-white">
        <Navbar />
        <main className="pt-16">
          <Routes>
            <Route path="/" element={<SchedulePage />} />
            <Route path="/rankings" element={<RankingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
