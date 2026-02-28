import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Home from './pages/Home';
import Learn from './pages/Learn';
import Infer from './pages/Infer';
import Marketplace from './pages/Marketplace';

function App() {
  return (
    <div className="min-h-screen flex flex-col font-sans text-slate-900 bg-slate-50">
      <Header />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/infer" element={<Infer />} />
          <Route path="/marketplace" element={<Marketplace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
