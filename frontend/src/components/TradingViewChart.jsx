import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode } from 'lightweight-charts';
import { motion } from 'framer-motion';
import { X, TrendingUp, TrendingDown, BarChart2, Clock } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const intervals = [
  { value: '1h', label: '1H' },
  { value: '4h', label: '4H' },
  { value: '1d', label: '1D' },
  { value: '1w', label: '1W' }
];

export default function TradingViewChart({ symbol, name, onClose, currentPrice, change24h }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  
  const [interval, setInterval] = useState('1d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ohlcData, setOhlcData] = useState([]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9CA3AF'
      },
      grid: {
        vertLines: { color: 'rgba(55, 65, 81, 0.5)' },
        horzLines: { color: 'rgba(55, 65, 81, 0.5)' }
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: '#00FFD1',
          width: 1,
          style: 2,
          labelBackgroundColor: '#00FFD1'
        },
        horzLine: {
          color: '#00FFD1',
          width: 1,
          style: 2,
          labelBackgroundColor: '#00FFD1'
        }
      },
      rightPriceScale: {
        borderColor: 'rgba(55, 65, 81, 0.5)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2
        }
      },
      timeScale: {
        borderColor: 'rgba(55, 65, 81, 0.5)',
        timeVisible: true,
        secondsVisible: false
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true
      }
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderUpColor: '#10B981',
      borderDownColor: '#EF4444',
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444'
    });

    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume'
      },
      priceScaleId: '',
      scaleMargins: {
        top: 0.85,
        bottom: 0
      }
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  useEffect(() => {
    fetchOHLCData();
  }, [symbol, interval]);

  const fetchOHLCData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`${API_URL}/api/crypto/ohlc/${symbol}`, {
        params: { interval, limit: 100 }
      });
      
      const candles = response.data.data;
      setOhlcData(candles);
      
      if (candleSeriesRef.current && volumeSeriesRef.current && candles.length > 0) {
        const candleData = candles.map(c => ({
          time: c.time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close
        }));
        
        const volumeData = candles.map(c => ({
          time: c.time,
          value: c.volume,
          color: c.close >= c.open ? 'rgba(16, 185, 129, 0.5)' : 'rgba(239, 68, 68, 0.5)'
        }));
        
        candleSeriesRef.current.setData(candleData);
        volumeSeriesRef.current.setData(volumeData);
        
        chartRef.current?.timeScale().fitContent();
      }
    } catch (err) {
      console.error('Error fetching OHLC data:', err);
      setError('Failed to load chart data');
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    if (!price) return '$0.00';
    if (price >= 1) return `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    return `$${price.toFixed(6)}`;
  };

  const getStats = () => {
    if (ohlcData.length < 2) return null;
    
    const latest = ohlcData[ohlcData.length - 1];
    const first = ohlcData[0];
    const high = Math.max(...ohlcData.map(c => c.high));
    const low = Math.min(...ohlcData.map(c => c.low));
    const avgVolume = ohlcData.reduce((sum, c) => sum + c.volume, 0) / ohlcData.length;
    
    return {
      high,
      low,
      change: ((latest.close - first.open) / first.open * 100).toFixed(2),
      avgVolume
    };
  };

  const stats = getStats();
  const isPositive = change24h >= 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="w-full max-w-5xl bg-gray-900 border border-gray-700 rounded-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-white">{symbol}</h2>
                <span className="text-gray-400 text-sm">{name}</span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-2xl font-bold text-white">
                  {formatPrice(currentPrice)}
                </span>
                <span className={`flex items-center gap-1 px-2 py-1 rounded-lg text-sm font-medium ${
                  isPositive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  {isPositive ? '+' : ''}{change24h?.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex bg-gray-800 rounded-lg p-1">
              {intervals.map(i => (
                <button
                  key={i.value}
                  onClick={() => setInterval(i.value)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                    interval === i.value
                      ? 'bg-[#00FFD1] text-gray-900'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {i.label}
                </button>
              ))}
            </div>
            
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700 transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        {stats && (
          <div className="px-4 py-2 border-b border-gray-700 flex gap-6 text-sm">
            <div>
              <span className="text-gray-500">High</span>
              <span className="ml-2 text-emerald-400 font-medium">{formatPrice(stats.high)}</span>
            </div>
            <div>
              <span className="text-gray-500">Low</span>
              <span className="ml-2 text-red-400 font-medium">{formatPrice(stats.low)}</span>
            </div>
            <div>
              <span className="text-gray-500">Period Change</span>
              <span className={`ml-2 font-medium ${parseFloat(stats.change) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {parseFloat(stats.change) >= 0 ? '+' : ''}{stats.change}%
              </span>
            </div>
            <div>
              <span className="text-gray-500">Avg Volume</span>
              <span className="ml-2 text-gray-300 font-medium">
                ${(stats.avgVolume / 1000000).toFixed(2)}M
              </span>
            </div>
          </div>
        )}
        
        <div className="relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
              <div className="flex items-center gap-3 text-gray-400">
                <BarChart2 className="w-6 h-6 animate-pulse" />
                <span>Loading chart...</span>
              </div>
            </div>
          )}
          
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 z-10">
              <div className="text-red-400 text-center">
                <p>{error}</p>
                <button
                  onClick={fetchOHLCData}
                  className="mt-2 px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-all"
                >
                  Retry
                </button>
              </div>
            </div>
          )}
          
          <div ref={chartContainerRef} className="w-full h-[400px]" />
        </div>
        
        <div className="p-3 border-t border-gray-700 flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>Data updates every {interval === '1h' ? 'minute' : '5 minutes'}</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Scroll to zoom</span>
            <span>Drag to pan</span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
