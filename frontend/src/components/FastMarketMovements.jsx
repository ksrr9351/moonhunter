import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Zap, X, ExternalLink, ChevronRight } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const FastMarketMovements = () => {
  const [fastMovers, setFastMovers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMover, setSelectedMover] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const fetchFastMovers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/crypto/fast-movers`);
      setFastMovers(response.data || []);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching fast movers:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFastMovers();
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchFastMovers();
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  // Generate sparkline data for visualization when API doesn't provide it
  const generateSparklineData = (change) => {
    const points = 8;
    const data = [];
    const isPositive = change > 0;
    
    for (let i = 0; i < points; i++) {
      const progress = i / (points - 1);
      const value = isPositive 
        ? 100 + (progress * Math.abs(change))
        : 100 - (progress * Math.abs(change));
      data.push({ value: value + (Math.random() * 2 - 1) });
    }
    return data;
  };

  // Open modal with mover details
  const openModal = (mover) => {
    setSelectedMover(mover);
    setShowModal(true);
  };

  // Close modal
  const closeModal = () => {
    setShowModal(false);
    setTimeout(() => setSelectedMover(null), 300);
  };

  if (loading) {
    return (
      <div className="fast-market-movements">
        <div className="section-header">
          <div className="flex items-center gap-3">
            <div className="icon-wrapper">
              <Zap className="w-6 h-6 text-[#00FFD1]" />
            </div>
            <div>
              <h2 className="section-title">Fast Market Movements</h2>
              <p className="section-subtitle">Real-time pump & dump detection</p>
            </div>
          </div>
        </div>
        
        <div className="movers-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="mover-card skeleton">
              <div className="skeleton-shimmer"></div>
            </div>
          ))}
        </div>

        <style jsx>{`
          .fast-market-movements {
            margin-top: 40px;
            animation: fadeInUp 0.6s ease-out;
          }

          .section-header {
            margin-bottom: 24px;
          }

          .icon-wrapper {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(0, 255, 209, 0.1), rgba(138, 43, 226, 0.1));
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(0, 255, 209, 0.2);
          }

          .section-title {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #00FFD1, #8A2BE2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }

          .section-subtitle {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.6);
            margin-top: 4px;
          }

          .movers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
          }

          .mover-card.skeleton {
            height: 180px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            position: relative;
            overflow: hidden;
          }

          .skeleton-shimmer {
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
              90deg,
              transparent,
              rgba(255, 255, 255, 0.1),
              transparent
            );
            animation: shimmer 1.5s infinite;
          }

          @keyframes shimmer {
            100% {
              left: 100%;
            }
          }

          @keyframes fadeInUp {
            from {
              opacity: 0;
              transform: translateY(20px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="fast-market-movements">
      <div className="section-header">
        <div className="flex items-center gap-3">
          <div className="icon-wrapper">
            <Zap className="w-6 h-6 text-[#00FFD1]" />
          </div>
          <div>
            <h2 className="section-title">Fast Market Movements</h2>
            <p className="section-subtitle">
              {fastMovers.length > 0 
                ? `${fastMovers.length} active ${fastMovers.length === 1 ? 'movement' : 'movements'} detected`
                : 'Monitoring markets in real-time...'}
            </p>
          </div>
        </div>
      </div>

      {fastMovers.length === 0 ? (
        <div className="empty-state">
          <Zap className="w-16 h-16 text-gray-600 mb-4" />
          <p className="empty-state-title">No fast movements detected yet</p>
          <p className="empty-state-subtitle">Monitoring markets every minute...</p>
        </div>
      ) : (
        <div className="movers-grid">
          {fastMovers.map((mover, index) => {
            const isPump = mover.movement_type === 'pump';
            const sparklineData = generateSparklineData(mover.price_change_percent);
            
            return (
              <div
                key={`${mover.symbol}-${index}`}
                className="mover-card"
                onClick={() => openModal(mover)}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="card-glow" style={{
                  background: isPump 
                    ? 'radial-gradient(circle at 50% 50%, rgba(50, 255, 126, 0.15), transparent)'
                    : 'radial-gradient(circle at 50% 50%, rgba(255, 77, 77, 0.15), transparent)'
                }}></div>

                <div className="card-header">
                  <div className="flex items-center gap-3">
                    {mover.logo ? (
                      <img src={mover.logo} alt={mover.name} className="coin-logo" />
                    ) : (
                      <div className="coin-logo-placeholder">{mover.symbol.charAt(0)}</div>
                    )}
                    <div>
                      <h3 className="coin-symbol">{mover.symbol}</h3>
                      <p className="coin-name">{mover.name}</p>
                    </div>
                  </div>
                  
                  <div className={`movement-badge ${isPump ? 'pump' : 'dump'}`}>
                    {isPump ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    {isPump ? 'PUMP' : 'DUMP'}
                  </div>
                </div>

                <div className="card-chart">
                  <ResponsiveContainer width="100%" height={50}>
                    <LineChart data={sparklineData}>
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke={isPump ? '#32ff7e' : '#ff4d4d'}
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                <div className="card-stats">
                  <div className="stat-item">
                    <span className="stat-label">Price</span>
                    <span className="stat-value">${mover.current_price.toLocaleString()}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Change</span>
                    <span className={`stat-value ${isPump ? 'text-green-400' : 'text-red-400'}`}>
                      {isPump ? '+' : ''}{mover.price_change_percent.toFixed(2)}%
                    </span>
                  </div>
                </div>

                <div className="card-footer">
                  <span className="timestamp">
                    {new Date(mover.timestamp).toLocaleTimeString()}
                  </span>
                  <ChevronRight className="w-4 h-4 text-gray-500" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {showModal && selectedMover && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>
              <X className="w-5 h-5" />
            </button>

            <div className="modal-header">
              <div className="flex items-center gap-4">
                {selectedMover.logo ? (
                  <img src={selectedMover.logo} alt={selectedMover.name} className="modal-coin-logo" />
                ) : (
                  <div className="modal-coin-logo-placeholder">{selectedMover.symbol.charAt(0)}</div>
                )}
                <div>
                  <h3 className="modal-title">{selectedMover.name}</h3>
                  <p className="modal-symbol">{selectedMover.symbol}</p>
                </div>
              </div>
              
              <div className={`modal-badge ${selectedMover.movement_type}`}>
                {selectedMover.movement_type === 'pump' ? (
                  <TrendingUp className="w-5 h-5" />
                ) : (
                  <TrendingDown className="w-5 h-5" />
                )}
                {selectedMover.movement_type.toUpperCase()}
              </div>
            </div>

            <div className="modal-stats">
              <div className="modal-stat-card">
                <span className="modal-stat-label">Current Price</span>
                <span className="modal-stat-value">${(selectedMover.current_price || selectedMover.price || 0).toLocaleString()}</span>
              </div>
              <div className="modal-stat-card">
                <span className="modal-stat-label">Market Cap</span>
                <span className="modal-stat-value">${(selectedMover.market_cap ? (selectedMover.market_cap / 1e9).toFixed(2) + 'B' : 'N/A')}</span>
              </div>
              <div className="modal-stat-card">
                <span className="modal-stat-label">Change</span>
                <span className={`modal-stat-value ${selectedMover.movement_type === 'pump' ? 'text-green-400' : 'text-red-400'}`}>
                  {selectedMover.price_change_percent > 0 ? '+' : ''}{(selectedMover.price_change_percent || 0).toFixed(2)}%
                </span>
              </div>
            </div>

            <div className="modal-actions">
              <button className="action-btn primary">
                <ExternalLink className="w-4 h-4" />
                Invest Now
              </button>
              <button className="action-btn secondary">
                View Details
              </button>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .fast-market-movements {
          margin-top: 40px;
          animation: fadeInUp 0.6s ease-out;
        }

        .section-header {
          margin-bottom: 24px;
        }

        .icon-wrapper {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background: linear-gradient(135deg, rgba(0, 255, 209, 0.1), rgba(138, 43, 226, 0.1));
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(0, 255, 209, 0.2);
          box-shadow: 0 0 20px rgba(0, 255, 209, 0.2);
        }

        .section-title {
          font-size: 24px;
          font-weight: 700;
          background: linear-gradient(135deg, #00FFD1, #8A2BE2);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .section-subtitle {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 60px 20px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
        }

        .empty-state-title {
          font-size: 18px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 16px;
          margin-bottom: 8px;
        }

        .empty-state-subtitle {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.4);
        }

        .movers-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
        }

        @media (max-width: 768px) {
          .movers-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (min-width: 768px) and (max-width: 1200px) {
          .movers-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        .mover-card {
          position: relative;
          padding: 20px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          cursor: pointer;
          transition: all 0.3s ease;
          backdrop-filter: blur(10px);
          overflow: hidden;
          animation: cardFadeIn 0.5s ease-out forwards;
          opacity: 0;
        }

        .mover-card:hover {
          background: rgba(255, 255, 255, 0.1);
          transform: translateY(-4px) scale(1.02);
          box-shadow: 0 8px 30px rgba(0, 255, 209, 0.2);
          border-color: rgba(0, 255, 209, 0.3);
        }

        .card-glow {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          pointer-events: none;
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .mover-card:hover .card-glow {
          opacity: 1;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .coin-logo {
          width: 40px;
          height: 40px;
          border-radius: 50%;
        }

        .coin-logo-placeholder {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: linear-gradient(135deg, #00FFD1, #8A2BE2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          color: white;
        }

        .coin-symbol {
          font-size: 18px;
          font-weight: 700;
          color: white;
        }

        .coin-name {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 2px;
        }

        .movement-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.5px;
        }

        .movement-badge.pump {
          background: rgba(50, 255, 126, 0.2);
          color: #32ff7e;
          border: 1px solid rgba(50, 255, 126, 0.3);
        }

        .movement-badge.dump {
          background: rgba(255, 77, 77, 0.2);
          color: #ff4d4d;
          border: 1px solid rgba(255, 77, 77, 0.3);
        }

        .card-chart {
          margin: 16px 0;
          height: 50px;
        }

        .card-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stat-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .stat-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.5);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .stat-value {
          font-size: 16px;
          font-weight: 700;
          color: white;
        }

        .card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .timestamp {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.4);
        }

        /* Modal Styles */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          backdrop-filter: blur(10px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          animation: fadeIn 0.3s ease-out;
          padding: 20px;
        }

        .modal-content {
          background: linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(31, 41, 55, 0.95));
          border: 1px solid rgba(0, 255, 209, 0.2);
          border-radius: 24px;
          padding: 32px;
          max-width: 500px;
          width: 100%;
          position: relative;
          animation: modalSlideUp 0.3s ease-out;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .modal-close {
          position: absolute;
          top: 20px;
          right: 20px;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          border: none;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .modal-close:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: scale(1.1);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .modal-coin-logo {
          width: 60px;
          height: 60px;
          border-radius: 50%;
        }

        .modal-coin-logo-placeholder {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: linear-gradient(135deg, #00FFD1, #8A2BE2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          font-weight: 700;
          color: white;
        }

        .modal-title {
          font-size: 24px;
          font-weight: 700;
          color: white;
        }

        .modal-symbol {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
        }

        .modal-badge {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          border-radius: 24px;
          font-size: 13px;
          font-weight: 700;
          letter-spacing: 0.5px;
        }

        .modal-badge.pump {
          background: rgba(50, 255, 126, 0.2);
          color: #32ff7e;
          border: 1px solid rgba(50, 255, 126, 0.3);
        }

        .modal-badge.dump {
          background: rgba(255, 77, 77, 0.2);
          color: #ff4d4d;
          border: 1px solid rgba(255, 77, 77, 0.3);
        }

        .modal-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
          margin: 24px 0;
        }

        .modal-stat-card {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .modal-stat-label {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.5);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .modal-stat-value {
          font-size: 18px;
          font-weight: 700;
          color: white;
        }

        .modal-actions {
          display: flex;
          gap: 12px;
          margin-top: 24px;
        }

        .action-btn {
          flex: 1;
          padding: 14px 24px;
          border-radius: 12px;
          font-weight: 600;
          font-size: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          cursor: pointer;
          transition: all 0.3s ease;
          border: none;
        }

        .action-btn.primary {
          background: linear-gradient(135deg, #00FFD1, #8A2BE2);
          color: white;
          box-shadow: 0 4px 20px rgba(0, 255, 209, 0.3);
        }

        .action-btn.primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 30px rgba(0, 255, 209, 0.5);
        }

        .action-btn.secondary {
          background: rgba(255, 255, 255, 0.1);
          color: white;
          border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .action-btn.secondary:hover {
          background: rgba(255, 255, 255, 0.15);
        }

        /* Animations */
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes cardFadeIn {
          to {
            opacity: 1;
          }
        }

        @keyframes modalSlideUp {
          from {
            opacity: 0;
            transform: translateY(30px) scale(0.9);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
};

export default FastMarketMovements;
