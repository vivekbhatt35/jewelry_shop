import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="container mt-5">
      <h1>Camera Management System</h1>
      <p className="lead">Welcome to the YOLO Pose Detection System</p>
      
      <div className="row mt-4">
        <div className="col-md-6">
          <div className="card mb-4">
            <div className="card-body">
              <h5 className="card-title">Cameras</h5>
              <p className="card-text">View and manage camera configurations</p>
              <Link href="/cameras" className="btn btn-primary">
                Manage Cameras
              </Link>
            </div>
          </div>
        </div>
        
        <div className="col-md-6">
          <div className="card mb-4">
            <div className="card-body">
              <h5 className="card-title">Alerts</h5>
              <p className="card-text">View recent alerts from detection system</p>
              <Link href="/alerts" className="btn btn-primary">
                View Alerts
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
