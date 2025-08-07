import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await axios.get(`${process.env.NEXT_PUBLIC_CAMERA_SERVICE_URL}/cameras`);
        setCameras(response.data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchCameras();
  }, []);

  if (loading) return <div className="container mt-5">Loading...</div>;
  if (error) return <div className="container mt-5">Error: {error}</div>;

  return (
    <div className="container mt-5">
      <h1>Camera Management</h1>
      <div className="row mt-4">
        {cameras.map((camera) => (
          <div key={camera.id} className="col-md-6 mb-4">
            <div className="card">
              <div className="card-body">
                <h5 className="card-title">Camera {camera.name}</h5>
                <p className="card-text">Status: {camera.status}</p>
                <p className="card-text">URL: {camera.url}</p>
                <button className="btn btn-primary me-2">
                  View Stream
                </button>
                <button className="btn btn-secondary">
                  Edit
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
