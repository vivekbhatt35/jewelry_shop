import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await axios.get(`${process.env.NEXT_PUBLIC_ALERT_SERVICE_URL}/alerts`);
        setAlerts(response.data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  if (loading) return <div className="container mt-5">Loading...</div>;
  if (error) return <div className="container mt-5">Error: {error}</div>;

  return (
    <div className="container mt-5">
      <h1>Detection Alerts</h1>
      <div className="row mt-4">
        {alerts.map((alert) => (
          <div key={alert.id} className="col-md-6 mb-4">
            <div className="card">
              <img src={alert.image_url} className="card-img-top" alt="Alert snapshot" />
              <div className="card-body">
                <h5 className="card-title">Alert from {alert.camera_name}</h5>
                <p className="card-text">Type: {alert.type}</p>
                <p className="card-text">Time: {new Date(alert.timestamp).toLocaleString()}</p>
                <button className="btn btn-primary">
                  View Details
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
