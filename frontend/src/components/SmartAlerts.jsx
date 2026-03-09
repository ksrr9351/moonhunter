import React, { useState, useEffect } from 'react';
import { Bell, Mail, Check, X, Smartphone, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { useWalletAuth } from '../contexts/WalletAuthContext';
import { pushNotificationService } from '../services/pushNotificationService';

const API_URL = import.meta.env.VITE_BACKEND_URL || '';

const SmartAlerts = () => {
  const { token } = useWalletAuth();
  const [alertSettings, setAlertSettings] = useState({
    email_alerts: false,
    threshold: 5,
    email: '',
    last_alert: null
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  const [pushSupported, setPushSupported] = useState(false);
  const [pushPermission, setPushPermission] = useState('default');
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);

  useEffect(() => {
    fetchAlertSettings();
    checkPushNotificationStatus();
  }, []);

  const checkPushNotificationStatus = async () => {
    const supported = pushNotificationService.isSupported();
    setPushSupported(supported);
    
    if (supported) {
      const permission = await pushNotificationService.getPermissionState();
      setPushPermission(permission);
      
      if (permission === 'granted') {
        const hasSubscription = await pushNotificationService.hasActiveSubscription();
        setPushEnabled(hasSubscription);
      }
    }
  };

  const fetchAlertSettings = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await axios.get(`${API_URL}/api/alert-settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data) {
        setAlertSettings(response.data);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching alert settings:', error);
      setLoading(false);
    }
  };

  const saveAlertSettings = async (newSettings) => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const response = await axios.post(
        `${API_URL}/api/alert-settings`,
        newSettings,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data) {
        setAlertSettings(response.data);
        setMessage({ type: 'success', text: 'Alert settings saved successfully!' });
        setTimeout(() => setMessage({ type: '', text: '' }), 3000);
      }
      setSaving(false);
    } catch (error) {
      console.error('Error saving alert settings:', error);
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' });
      setSaving(false);
    }
  };

  const handleToggle = () => {
    const newSettings = { ...alertSettings, email_alerts: !alertSettings.email_alerts };
    setAlertSettings(newSettings);
    saveAlertSettings(newSettings);
  };

  const handleThresholdChange = (threshold) => {
    const newSettings = { ...alertSettings, threshold };
    setAlertSettings(newSettings);
    saveAlertSettings(newSettings);
  };

  const handleEmailChange = (e) => {
    setAlertSettings({ ...alertSettings, email: e.target.value });
  };

  const handleEmailSave = () => {
    saveAlertSettings(alertSettings);
  };

  const handlePushToggle = async () => {
    if (!token) {
      setMessage({ type: 'error', text: 'Please connect your wallet first' });
      return;
    }

    setPushLoading(true);
    setMessage({ type: '', text: '' });

    try {
      if (!pushEnabled) {
        const initialized = await pushNotificationService.init();
        if (!initialized) {
          setMessage({ type: 'error', text: 'Push notifications are not supported on this browser' });
          setPushLoading(false);
          return;
        }

        const permissionGranted = await pushNotificationService.requestPermission();
        setPushPermission(permissionGranted ? 'granted' : 'denied');
        
        if (!permissionGranted) {
          setMessage({ type: 'error', text: 'Please allow notifications in your browser settings' });
          setPushLoading(false);
          return;
        }

        const subscription = await pushNotificationService.subscribe(token);
        if (subscription) {
          setPushEnabled(true);
          setMessage({ type: 'success', text: 'Push notifications enabled!' });
        } else {
          setMessage({ type: 'error', text: 'Failed to enable push notifications' });
        }
      } else {
        const success = await pushNotificationService.unsubscribe(token);
        if (success) {
          setPushEnabled(false);
          setMessage({ type: 'success', text: 'Push notifications disabled' });
        } else {
          setMessage({ type: 'error', text: 'Failed to disable push notifications' });
        }
      }
    } catch (error) {
      console.error('Push notification error:', error);
      setMessage({ type: 'error', text: 'An error occurred. Please try again.' });
    }

    setPushLoading(false);
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const sendTestPush = async () => {
    if (!token || !pushEnabled) return;
    
    try {
      await axios.post(
        `${API_URL}/api/push/test`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessage({ type: 'success', text: 'Test notification sent!' });
      setTimeout(() => setMessage({ type: '', text: '' }), 3000);
    } catch (error) {
      console.error('Error sending test notification:', error);
      setMessage({ type: 'error', text: 'Failed to send test notification' });
    }
  };

  if (loading) {
    return (
      <div className="smart-alerts">
        <div className="alerts-header">
          <div className="flex items-center gap-3">
            <div className="icon-wrapper">
              <Bell className="w-6 h-6 text-[#00FFD1]" />
            </div>
            <div>
              <h2 className="section-title">Smart Alerts</h2>
              <p className="section-subtitle">Loading...</p>
            </div>
          </div>
        </div>
        
        <style jsx>{`
          .smart-alerts {
            margin-top: 40px;
          }
          .alerts-header {
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
        `}</style>
      </div>
    );
  }

  return (
    <div className="smart-alerts">
      <div className="alerts-header">
        <div className="flex items-center gap-3">
          <div className="icon-wrapper">
            <Bell className="w-6 h-6 text-[#00FFD1]" />
          </div>
          <div>
            <h2 className="section-title">Smart Alerts</h2>
            <p className="section-subtitle">Get notified on significant market movements</p>
          </div>
        </div>
      </div>

      <div className="alerts-card">
        {/* Push Notifications Toggle */}
        <div className="alert-setting-row">
          <div className="setting-info">
            <div className="flex items-center gap-2">
              <Smartphone className="w-5 h-5 text-[#8B5CF6]" />
              <h3 className="setting-title">Push Notifications</h3>
              {!pushSupported && (
                <span className="unsupported-badge">Not Supported</span>
              )}
            </div>
            <p className="setting-description">
              Get instant browser notifications for price alerts and AI signals
            </p>
            {pushPermission === 'denied' && (
              <p className="permission-warning">
                <AlertCircle className="w-4 h-4 inline mr-1" />
                Notifications blocked. Please enable in browser settings.
              </p>
            )}
          </div>
          
          <div className="toggle-actions">
            {pushEnabled && (
              <button
                onClick={sendTestPush}
                className="test-btn"
                disabled={pushLoading}
              >
                Test
              </button>
            )}
            <button
              onClick={handlePushToggle}
              disabled={!pushSupported || pushLoading || pushPermission === 'denied'}
              className={`toggle-switch ${pushEnabled ? 'active' : ''} ${!pushSupported || pushPermission === 'denied' ? 'disabled' : ''}`}
            >
              <div className="toggle-slider"></div>
            </button>
          </div>
        </div>

        {/* Email Alerts Toggle */}
        <div className="alert-setting-row" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '20px', marginTop: '20px' }}>
          <div className="setting-info">
            <div className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-[#00FFD1]" />
              <h3 className="setting-title">Email Notifications</h3>
            </div>
            <p className="setting-description">
              Receive email alerts when crypto prices move significantly
            </p>
          </div>
          
          <button
            onClick={handleToggle}
            disabled={saving}
            className={`toggle-switch ${alertSettings.email_alerts ? 'active' : ''}`}
          >
            <div className="toggle-slider"></div>
          </button>
        </div>

        {/* Email Input */}
        {alertSettings.email_alerts && (
          <div className="email-input-section">
            <label className="input-label">Email Address</label>
            <div className="input-group">
              <input
                type="email"
                value={alertSettings.email}
                onChange={handleEmailChange}
                placeholder="your.email@example.com"
                className="email-input"
              />
              <button
                onClick={handleEmailSave}
                disabled={saving || !alertSettings.email}
                className="save-btn"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        )}

        {/* Threshold Selection */}
        {alertSettings.email_alerts && (
          <div className="threshold-section">
            <h3 className="threshold-title">Alert Threshold</h3>
            <p className="threshold-description">
              Get notified when price changes by:
            </p>
            <div className="threshold-options">
              {[5, 10, 15].map((value) => (
                <button
                  key={value}
                  onClick={() => handleThresholdChange(value)}
                  disabled={saving}
                  className={`threshold-btn ${alertSettings.threshold === value ? 'active' : ''}`}
                >
                  {value}%
                  {alertSettings.threshold === value && (
                    <Check className="w-4 h-4 ml-2" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Last Alert Info */}
        {alertSettings.last_alert && (
          <div className="last-alert-info">
            <span className="last-alert-label">Last alert sent:</span>
            <span className="last-alert-time">
              {new Date(alertSettings.last_alert).toLocaleString()}
            </span>
          </div>
        )}

        {/* Message */}
        {message.text && (
          <div className={`message ${message.type}`}>
            {message.type === 'success' ? (
              <Check className="w-4 h-4" />
            ) : (
              <X className="w-4 h-4" />
            )}
            {message.text}
          </div>
        )}
      </div>

      <style jsx>{`
        .smart-alerts {
          margin-top: 40px;
          animation: fadeInUp 0.6s ease-out;
        }

        .alerts-header {
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

        .alerts-card {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          padding: 24px;
          backdrop-filter: blur(10px);
        }

        .alert-setting-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .setting-info {
          flex: 1;
        }

        .setting-title {
          font-size: 18px;
          font-weight: 600;
          color: white;
          margin-bottom: 4px;
        }

        .setting-description {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.6);
          margin-top: 4px;
        }

        .unsupported-badge {
          font-size: 11px;
          padding: 2px 8px;
          background: rgba(255, 77, 77, 0.2);
          border: 1px solid rgba(255, 77, 77, 0.3);
          border-radius: 4px;
          color: #ff6b6b;
          font-weight: 500;
        }

        .permission-warning {
          font-size: 12px;
          color: #FBBF24;
          margin-top: 8px;
          display: flex;
          align-items: center;
        }

        .toggle-actions {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .test-btn {
          padding: 8px 16px;
          background: rgba(139, 92, 246, 0.2);
          border: 1px solid rgba(139, 92, 246, 0.3);
          border-radius: 8px;
          color: #A78BFA;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .test-btn:hover:not(:disabled) {
          background: rgba(139, 92, 246, 0.3);
          border-color: rgba(139, 92, 246, 0.5);
        }

        .test-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .toggle-switch {
          width: 60px;
          height: 32px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 16px;
          position: relative;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .toggle-switch:hover:not(.disabled) {
          background: rgba(255, 255, 255, 0.15);
        }

        .toggle-switch.active {
          background: linear-gradient(135deg, #00FFD1, #8A2BE2);
          border-color: transparent;
        }

        .toggle-switch.disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }

        .toggle-slider {
          width: 24px;
          height: 24px;
          background: white;
          border-radius: 50%;
          position: absolute;
          top: 3px;
          left: 4px;
          transition: transform 0.3s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .toggle-switch.active .toggle-slider {
          transform: translateX(28px);
        }

        .email-input-section {
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .input-label {
          display: block;
          font-size: 13px;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.8);
          margin-bottom: 8px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .input-group {
          display: flex;
          gap: 12px;
        }

        .email-input {
          flex: 1;
          padding: 12px 16px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          color: white;
          font-size: 14px;
          transition: all 0.2s ease;
        }

        .email-input:focus {
          outline: none;
          border-color: #00FFD1;
          box-shadow: 0 0 0 3px rgba(0, 255, 209, 0.1);
        }

        .email-input::placeholder {
          color: rgba(255, 255, 255, 0.4);
        }

        .save-btn {
          padding: 12px 24px;
          background: linear-gradient(135deg, #00FFD1, #8A2BE2);
          border: none;
          border-radius: 8px;
          color: white;
          font-weight: 600;
          font-size: 14px;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .save-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 255, 209, 0.3);
        }

        .save-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .threshold-section {
          margin-top: 20px;
          padding-top: 20px;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .threshold-title {
          font-size: 16px;
          font-weight: 600;
          color: white;
          margin-bottom: 4px;
        }

        .threshold-description {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.6);
          margin-bottom: 16px;
        }

        .threshold-options {
          display: flex;
          gap: 12px;
        }

        .threshold-btn {
          flex: 1;
          padding: 12px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          color: white;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .threshold-btn:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.1);
          border-color: rgba(0, 255, 209, 0.3);
        }

        .threshold-btn.active {
          background: linear-gradient(135deg, rgba(0, 255, 209, 0.2), rgba(138, 43, 226, 0.2));
          border-color: #00FFD1;
        }

        .threshold-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .last-alert-info {
          margin-top: 20px;
          padding: 12px 16px;
          background: rgba(0, 255, 209, 0.05);
          border: 1px solid rgba(0, 255, 209, 0.2);
          border-radius: 8px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .last-alert-label {
          font-size: 13px;
          color: rgba(255, 255, 255, 0.6);
        }

        .last-alert-time {
          font-size: 13px;
          font-weight: 600;
          color: #00FFD1;
        }

        .message {
          margin-top: 16px;
          padding: 12px 16px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          animation: slideIn 0.3s ease-out;
        }

        .message.success {
          background: rgba(50, 255, 126, 0.1);
          border: 1px solid rgba(50, 255, 126, 0.3);
          color: #32ff7e;
        }

        .message.error {
          background: rgba(255, 77, 77, 0.1);
          border: 1px solid rgba(255, 77, 77, 0.3);
          color: #ff4d4d;
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

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
};

export default SmartAlerts;
