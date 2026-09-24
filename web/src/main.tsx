import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./vendor/katex/katex.min.css";
import "./styles/foundation.css";
import "./styles/components.css";
import "./styles/shell.css";
import "./styles/dashboard.css";
import "./styles/training.css";
import "./styles/exercises.css";
import "./styles/question-bank.css";
import "./styles/mock-labs.css";
import "./styles/insights.css";
import "./styles/jd-analysis.css";
import "./styles/management.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
