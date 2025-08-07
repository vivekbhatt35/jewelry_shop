import React from 'react';
import 'bootstrap/dist/css/bootstrap.min.css';
import '../styles/globals.css';

function MyApp({ Component, pageProps }) {
  return (
    <div>
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container">
          <a className="navbar-brand" href="/">Camera Management System</a>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav">
              <li className="nav-item">
                <a className="nav-link" href="/">Home</a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/cameras">Cameras</a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/alerts">Alerts</a>
              </li>
            </ul>
          </div>
        </div>
      </nav>
      <main>
        <Component {...pageProps} />
      </main>
      <footer className="footer mt-auto py-3 bg-light">
        <div className="container text-center">
          <span className="text-muted">YOLO Pose Detection System &copy; 2025</span>
        </div>
      </footer>
    </div>
  );
}

export default MyApp;
