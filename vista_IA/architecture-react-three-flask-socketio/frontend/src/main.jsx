import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./App.css";

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <main className="runtime-error-screen">
        <section className="runtime-error-card">
          <p className="eyebrow">Frontend Error</p>
          <h1>La interfaz encontro un error de runtime</h1>
          <p>Recarga la pagina. Si el error persiste, comparte este mensaje para corregirlo mas rapido.</p>
          <pre>{String(this.state.error?.stack || this.state.error?.message || this.state.error)}</pre>
        </section>
      </main>
    );
  }
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>
);
