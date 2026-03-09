import React, { Suspense, lazy, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { WalletAuthProvider } from "./contexts/WalletAuthContext";
import { EventProvider } from "./contexts/EventContext";
import { PriceStreamProvider } from "./contexts/PriceStreamContext";
import ProtectedRoute from "./components/ProtectedRoute";

// Lazy load all page components for code splitting
const HomePage = lazy(() => import("./components/HomePage"));
const DynamicDashboard = lazy(() => import("./components/DynamicDashboard"));
const TopGainersPage = lazy(() => import("./components/TopGainersPage"));
const InvestPage = lazy(() => import("./components/InvestPage"));
const WalletPage = lazy(() => import("./components/WalletPage"));
const AIAutoInvestPage = lazy(() => import("./components/AIAutoInvestPage"));
const AIEnginePage = lazy(() => import("./components/AIEnginePage"));
const LeaderboardPage = lazy(() => import("./components/LeaderboardPage"));
const BacktestPage = lazy(() => import("./components/BacktestPage"));

// Preload critical routes after initial render
const preloadCriticalRoutes = () => {
  import("./components/DynamicDashboard");
  import("./components/WalletPage");
};

const PageLoader = () => (
  <div className="premium-bg min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className="w-12 h-12 border-4 border-[#00FFD1]/30 border-t-[#00FFD1] rounded-full animate-spin mx-auto mb-4"></div>
      <p className="text-gray-400">Loading...</p>
    </div>
  </div>
);

function App() {
  // Preload critical routes after initial render for faster navigation
  useEffect(() => {
    const timer = setTimeout(preloadCriticalRoutes, 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="App">
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <WalletAuthProvider>
          <EventProvider>
            <PriceStreamProvider>
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route
                    path="/dashboard"
                    element={
                      <ProtectedRoute>
                        <DynamicDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/top-gainers"
                    element={
                      <ProtectedRoute>
                        <TopGainersPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/invest"
                    element={
                      <ProtectedRoute>
                        <InvestPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/wallet"
                    element={
                      <ProtectedRoute>
                        <WalletPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/ai-auto-invest"
                    element={
                      <ProtectedRoute>
                        <AIAutoInvestPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/ai-engine"
                    element={
                      <ProtectedRoute>
                        <AIEnginePage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/leaderboard" element={<LeaderboardPage />} />
                  <Route path="/backtest" element={<BacktestPage />} />
                </Routes>
              </Suspense>
            </PriceStreamProvider>
          </EventProvider>
        </WalletAuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
