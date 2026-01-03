import React from "react"
import ReactDOM from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import App from "./App"
import "./styles/index.css"

// Initialize i18n before React renders - must be imported at entry point
import "./i18n"

ReactDOM.createRoot(document.getElementById("root")).render(
  // StrictMode desabilitado temporariamente - causa flickering
  // <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </BrowserRouter>
  // </React.StrictMode>,
)
