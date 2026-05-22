import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<div>Dashboard coming soon</div>} />
        <Route path="/interview/:id" element={<div>Interview Room</div>} />
        <Route path="/report/:id" element={<div>Report</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App