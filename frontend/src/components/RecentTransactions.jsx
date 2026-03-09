import React, { useState, useEffect } from 'react';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import axios from 'axios';
import { Search, History, TrendingUp, TrendingDown, DollarSign, Trash2, ArrowUpCircle, ArrowDownCircle, Zap } from 'lucide-react';
import { formatUSD } from '../utils/formatters';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const RecentTransactions = ({ limit = null, showTitle = true }) => {
  const { token } = useWalletAuth();
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTransactions();
  }, []);

  useEffect(() => {
    filterTransactions();
  }, [searchQuery, transactions]);

  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/api/transactions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('Error fetching transactions:', error);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  const filterTransactions = () => {
    if (!searchQuery.trim()) {
      const filtered = limit ? transactions.slice(0, limit) : transactions;
      setFilteredTransactions(filtered);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = transactions.filter(tx => {
      const matchAmount = tx.amount?.toString().includes(query);
      const matchTotal = tx.total?.toString().includes(query);
      const matchType = tx.type?.toLowerCase().includes(query);
      const matchToken = tx.token_symbol?.toLowerCase().includes(query);
      const matchDate = new Date(tx.timestamp).toLocaleDateString().toLowerCase().includes(query);
      
      return matchAmount || matchTotal || matchType || matchToken || matchDate;
    });

    const result = limit ? filtered.slice(0, limit) : filtered;
    setFilteredTransactions(result);
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear all transaction history? This action cannot be undone.')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/transactions/clear`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions([]);
      setFilteredTransactions([]);
      alert('Transaction history cleared successfully!');
    } catch (error) {
      console.error('Error clearing transactions:', error);
      alert('Failed to clear transaction history. Please try again.');
    }
  };

  const getTransactionIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'deposit':
        return <ArrowDownCircle className="w-5 h-5 text-[#00FFD1]" />;
      case 'withdraw':
        return <ArrowUpCircle className="w-5 h-5 text-red-400" />;
      case 'invest':
        return <Zap className="w-5 h-5 text-yellow-400" />;
      default:
        return <DollarSign className="w-5 h-5 text-gray-400" />;
    }
  };

  const getTransactionColor = (type) => {
    switch (type?.toLowerCase()) {
      case 'deposit':
        return 'text-[#00FFD1]';
      case 'withdraw':
        return 'text-red-400';
      case 'invest':
        return 'text-yellow-400';
      default:
        return 'text-gray-400';
    }
  };

  if (loading) {
    return (
      <div className="premium-glass-card p-6">
        <div className="flex items-center justify-center h-40">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#00FFD1] border-t-transparent"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="premium-glass-card p-6">
      {/* Header */}
      {showTitle && (
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-[#00FFD1]" />
            Recent Transactions
          </h2>
          {transactions.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 text-sm font-medium transition-all hover:scale-105"
            >
              <Trash2 className="w-4 h-4" />
              Clear History
            </button>
          )}
        </div>
      )}

      {/* Search Bar */}
      {transactions.length > 0 && (
        <div className="relative mb-4">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by amount, type, token, or date..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFD1]/50 transition-all"
          />
        </div>
      )}

      {/* Transactions List */}
      {filteredTransactions.length === 0 ? (
        <div className="text-center py-12">
          <History className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 text-lg mb-2">
            {searchQuery ? 'No matching transactions' : 'No transactions yet'}
          </p>
          <p className="text-gray-500 text-sm">
            {searchQuery ? 'Try a different search term' : 'Your transaction history will appear here'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTransactions.map((tx) => (
            <div
              key={tx.transaction_id}
              className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-[#00FFD1]/30 hover:bg-white/10 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center group-hover:bg-[#00FFD1]/10 transition-all">
                    {getTransactionIcon(tx.type)}
                  </div>
                  <div>
                    <p className={`font-semibold ${getTransactionColor(tx.type)} capitalize`}>
                      {tx.type}
                    </p>
                    <p className="text-xs text-gray-400">
                      {tx.token_symbol && `${tx.amount} ${tx.token_symbol} @ ${formatUSD(tx.price)}`}
                      {!tx.token_symbol && new Date(tx.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-white">{formatUSD(tx.total)}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(tx.timestamp).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecentTransactions;
