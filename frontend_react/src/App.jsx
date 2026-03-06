import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Home from './pages/Home';
import Learn from './pages/Learn';
import Infer from './pages/Infer';
import Marketplace from './pages/Marketplace';
import PiUnified from './pages/PiUnified';

function App() {
  const location = useLocation();
  const isPi = location.pathname.startsWith('/pi');

  return (
    <div className={`min-height-screen flex flex-col font-sans ${isPi ? 'bg-slate-900' : 'bg-slate-50 text-slate-900'}`}>
      {!isPi && <Header />}
      <main className="flex-1">
        <Routes>
          {/* Main Web App Routes */}
          <Route path="/" element={<Marketplace />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/infer" element={<Infer />} />
          <Route path="/marketplace" element={<Marketplace />} />

          {/* Raspberry Pi Specific Routes (Unified Single Page) */}
          <Route path="/pi" element={<PiUnified />} />
          <Route path="/pi/*" element={<PiUnified />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
