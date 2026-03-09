import { motion, AnimatePresence } from 'framer-motion';
import { usePriceStream } from '../contexts/PriceStreamContext';

export function LivePriceIndicator({ symbol, showDetails = false }) {
  const { getPrice, isConnected } = usePriceStream();
  const priceData = getPrice(symbol);

  if (!priceData) {
    return null;
  }

  const priceChange = priceData.percent_change_1h || 0;
  const isPositive = priceChange >= 0;

  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-sm">
        ${priceData.price?.toLocaleString(undefined, { 
          minimumFractionDigits: 2, 
          maximumFractionDigits: priceData.price < 1 ? 6 : 2 
        })}
      </span>
      {showDetails && (
        <span className={`text-xs ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{priceChange.toFixed(2)}%
        </span>
      )}
      {isConnected && (
        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" title="Live" />
      )}
    </div>
  );
}

export function LiveConnectionStatus() {
  const { isConnected, lastUpdate } = usePriceStream();

  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
      <span>{isConnected ? 'Live' : 'Disconnected'}</span>
      {lastUpdate && (
        <span className="text-gray-500">
          Updated {lastUpdate.toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}

export function LivePriceCard({ symbol, name, logo }) {
  const { getPrice, isConnected } = usePriceStream();
  const priceData = getPrice(symbol);

  if (!priceData) {
    return null;
  }

  const change1h = priceData.percent_change_1h || 0;
  const change24h = priceData.percent_change_24h || 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800/50 rounded-lg p-3 border border-gray-700"
    >
      <div className="flex items-center gap-3">
        {(logo || priceData.logo) && (
          <img 
            src={logo || priceData.logo} 
            alt={symbol} 
            className="w-8 h-8 rounded-full"
          />
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">{symbol}</span>
            {isConnected && (
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            )}
          </div>
          <span className="text-xs text-gray-400">{name || priceData.name}</span>
        </div>
        <div className="text-right">
          <div className="font-mono text-white">
            ${priceData.price?.toLocaleString(undefined, { 
              minimumFractionDigits: 2, 
              maximumFractionDigits: priceData.price < 1 ? 6 : 2 
            })}
          </div>
          <div className="flex gap-2 text-xs">
            <span className={change1h >= 0 ? 'text-green-400' : 'text-red-400'}>
              1h: {change1h >= 0 ? '+' : ''}{change1h.toFixed(2)}%
            </span>
            <span className={change24h >= 0 ? 'text-green-400' : 'text-red-400'}>
              24h: {change24h >= 0 ? '+' : ''}{change24h.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function FastMoverAlert({ coin }) {
  if (!coin) return null;

  const isPositive = (coin.change || coin.percent_change_1h || 0) >= 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: 50 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -50 }}
      className={`p-3 rounded-lg border ${
        isPositive 
          ? 'bg-green-900/30 border-green-600' 
          : 'bg-red-900/30 border-red-600'
      }`}
    >
      <div className="flex items-center gap-2">
        {coin.logo && (
          <img src={coin.logo} alt={coin.symbol} className="w-6 h-6 rounded-full" />
        )}
        <span className="font-semibold">{coin.symbol}</span>
        <span className={isPositive ? 'text-green-400' : 'text-red-400'}>
          {isPositive ? '+' : ''}{(coin.change || coin.percent_change_1h || 0).toFixed(2)}%
        </span>
      </div>
    </motion.div>
  );
}

export function LivePriceTicker() {
  const { prices, isConnected } = usePriceStream();
  const topCoins = Object.values(prices).slice(0, 10);

  if (!isConnected || topCoins.length === 0) {
    return null;
  }

  return (
    <div className="overflow-hidden bg-gray-900/50 border-b border-gray-800">
      <motion.div 
        className="flex gap-6 py-2 px-4"
        animate={{ x: [0, -1000] }}
        transition={{ 
          duration: 30, 
          repeat: Infinity, 
          ease: "linear" 
        }}
      >
        {[...topCoins, ...topCoins].map((coin, index) => (
          <div key={`${coin.symbol}-${index}`} className="flex items-center gap-2 whitespace-nowrap">
            <span className="text-gray-400">{coin.symbol}</span>
            <span className="font-mono text-white">
              ${coin.price?.toLocaleString(undefined, { 
                minimumFractionDigits: 2, 
                maximumFractionDigits: coin.price < 1 ? 4 : 2 
              })}
            </span>
            <span className={`text-xs ${(coin.percent_change_1h || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {(coin.percent_change_1h || 0) >= 0 ? '+' : ''}{(coin.percent_change_1h || 0).toFixed(2)}%
            </span>
          </div>
        ))}
      </motion.div>
    </div>
  );
}

export default LivePriceIndicator;
