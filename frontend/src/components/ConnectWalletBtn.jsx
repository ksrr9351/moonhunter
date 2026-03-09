import React, { useState } from 'react';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { Wallet, LogOut, ChevronDown } from 'lucide-react';

const ConnectWalletBtn = () => {
  const { walletConnected, walletAddress, connectWallet, logout } = useWalletAuth();
  const [showDropdown, setShowDropdown] = useState(false);

  // Format wallet address for display
  const formatAddress = (address) => {
    if (!address) return '';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  if (walletConnected && walletAddress) {
    // Show connected wallet with dropdown
    return (
      <div className="wallet-connected-container" style={{ position: 'relative' }}>
        <button
          className="wallet-connected-btn"
          onClick={() => setShowDropdown(!showDropdown)}
        >
          <Wallet size={18} />
          <span className="wallet-address">{formatAddress(walletAddress)}</span>
          <ChevronDown size={16} />
        </button>

        {showDropdown && (
          <div className="wallet-dropdown">
            <div className="wallet-dropdown-address">
              <span className="label">Connected Wallet</span>
              <span className="address">{walletAddress}</span>
            </div>
            <button className="wallet-dropdown-logout" onClick={logout}>
              <LogOut size={16} />
              Disconnect
            </button>
          </div>
        )}

        <style jsx>{`
          .wallet-connected-container {
            position: relative;
          }

          .wallet-connected-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            background: rgba(0, 255, 209, 0.1);
            border: 1.5px solid rgba(0, 255, 209, 0.3);
            border-radius: 12px;
            color: #00FFD1;
            font-weight: 500;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
          }

          .wallet-connected-btn:hover {
            background: rgba(0, 255, 209, 0.2);
            border-color: rgba(0, 255, 209, 0.5);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 255, 209, 0.2);
          }

          .wallet-address {
            font-family: 'Courier New', monospace;
            letter-spacing: 0.5px;
          }

          .wallet-dropdown {
            position: absolute;
            top: calc(100% + 8px);
            right: 0;
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid rgba(0, 255, 209, 0.3);
            border-radius: 12px;
            padding: 12px;
            min-width: 280px;
            z-index: 1000;
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
          }

          .wallet-dropdown-address {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 12px;
            background: rgba(0, 255, 209, 0.05);
            border-radius: 8px;
            margin-bottom: 8px;
          }

          .wallet-dropdown-address .label {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.6);
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }

          .wallet-dropdown-address .address {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #00FFD1;
            word-break: break-all;
          }

          .wallet-dropdown-logout {
            width: 100%;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            background: rgba(255, 107, 107, 0.1);
            border: 1px solid rgba(255, 107, 107, 0.3);
            border-radius: 8px;
            color: #FF6B6B;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .wallet-dropdown-logout:hover {
            background: rgba(255, 107, 107, 0.2);
            border-color: rgba(255, 107, 107, 0.5);
          }
        `}</style>
      </div>
    );
  }

  // Show connect wallet button
  return (
    <button className="connect-wallet-btn" onClick={connectWallet}>
      <Wallet size={18} />
      <span>Connect Wallet</span>

      <style jsx>{`
        .connect-wallet-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 10px 16px;
          background: linear-gradient(135deg, #00FFD1 0%, #00C8A5 100%);
          border: none;
          border-radius: 12px;
          color: #111827;
          font-weight: 600;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 12px rgba(0, 255, 209, 0.3);
          white-space: nowrap;
        }

        @media (min-width: 1024px) {
          .connect-wallet-btn {
            gap: 8px;
            padding: 12px 24px;
            font-size: 15px;
          }
        }

        .connect-wallet-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(0, 255, 209, 0.4);
        }

        .connect-wallet-btn:active {
          transform: translateY(0);
        }
      `}</style>
    </button>
  );
};

export default ConnectWalletBtn;
