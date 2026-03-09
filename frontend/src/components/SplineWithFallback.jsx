import React, { useState, useEffect, Suspense, lazy } from 'react';

const Spline = lazy(() => import('@splinetool/react-spline'));

const CryptoFallbackVisual = () => {
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <div className="crypto-visual-fallback">
        <div className="orbit-ring orbit-ring-1">
          <div className="orbit-dot"></div>
        </div>
        <div className="orbit-ring orbit-ring-2">
          <div className="orbit-dot"></div>
        </div>
        <div className="orbit-ring orbit-ring-3">
          <div className="orbit-dot"></div>
        </div>
        <div className="central-orb">
          <div className="orb-glow"></div>
          <span className="orb-symbol">M</span>
        </div>
      </div>
      <style>{`
        .crypto-visual-fallback {
          position: relative;
          width: 400px;
          height: 400px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .orbit-ring {
          position: absolute;
          border: 1px solid rgba(0, 255, 209, 0.2);
          border-radius: 50%;
          animation: spin 20s linear infinite;
        }
        .orbit-ring-1 {
          width: 200px;
          height: 200px;
          animation-duration: 15s;
        }
        .orbit-ring-2 {
          width: 300px;
          height: 300px;
          animation-duration: 25s;
          animation-direction: reverse;
        }
        .orbit-ring-3 {
          width: 380px;
          height: 380px;
          animation-duration: 35s;
        }
        .orbit-dot {
          position: absolute;
          width: 10px;
          height: 10px;
          background: linear-gradient(135deg, #00FFD1, #00A896);
          border-radius: 50%;
          top: -5px;
          left: 50%;
          transform: translateX(-50%);
          box-shadow: 0 0 20px rgba(0, 255, 209, 0.8);
        }
        .central-orb {
          width: 120px;
          height: 120px;
          background: linear-gradient(135deg, rgba(0, 255, 209, 0.3), rgba(0, 168, 150, 0.1));
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          border: 2px solid rgba(0, 255, 209, 0.5);
          animation: pulse 3s ease-in-out infinite;
        }
        .orb-glow {
          position: absolute;
          width: 100%;
          height: 100%;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(0, 255, 209, 0.4) 0%, transparent 70%);
          animation: glow 2s ease-in-out infinite alternate;
        }
        .orb-symbol {
          font-size: 48px;
          font-weight: bold;
          color: #00FFD1;
          text-shadow: 0 0 30px rgba(0, 255, 209, 0.8);
          z-index: 1;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
        @keyframes glow {
          from { opacity: 0.5; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

const LoadingFallback = () => (
  <div className="w-full h-full flex items-center justify-center">
    <div className="animate-pulse">
      <CryptoFallbackVisual />
    </div>
  </div>
);

class SplineErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.log('Spline 3D failed to load, using fallback:', error.message);
  }

  render() {
    if (this.state.hasError) {
      return <CryptoFallbackVisual />;
    }
    return this.props.children;
  }
}

const SplineWithFallback = ({ scene, style, ...props }) => {
  const [webglSupported, setWebglSupported] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) {
        setWebglSupported(false);
      }
    } catch (e) {
      setWebglSupported(false);
    }
  }, []);

  if (!webglSupported || loadError) {
    return <CryptoFallbackVisual />;
  }

  return (
    <SplineErrorBoundary>
      <Suspense fallback={<LoadingFallback />}>
        <Spline 
          scene={scene} 
          style={style}
          onError={() => setLoadError(true)}
          {...props}
        />
      </Suspense>
    </SplineErrorBoundary>
  );
};

export default SplineWithFallback;
