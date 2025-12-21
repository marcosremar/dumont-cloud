import { useState } from "react";
import { X, Code, Key } from "lucide-react";

/**
 * DevBar - Development mode information bar
 * Only visible when import.meta.env.DEV === true (npm run dev)
 */
const DevBar = () => {
  const [isVisible, setIsVisible] = useState(true);

  // Hide in production builds
  if (import.meta.env.PROD) {
    return null;
  }

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        style={{
          position: "fixed",
          bottom: "8px",
          right: "8px",
          zIndex: 999999,
          background: "#f59e0b",
          color: "black",
          padding: "6px",
          borderRadius: "50%",
          border: "none",
          cursor: "pointer",
          boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
        }}
        title="Show Dev Bar"
      >
        <Code size={14} />
      </button>
    );
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 999999,
        background: "linear-gradient(to right, #f59e0b, #ea580c)",
        color: "black",
        padding: "4px 12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontFamily: "system-ui, sans-serif",
        fontSize: "11px",
        boxShadow: "0 -2px 8px rgba(0,0,0,0.15)"
      }}
    >
      {/* Left side */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px", fontWeight: "bold" }}>
          <Code size={12} />
          <span>DEV</span>
        </div>

        {/* Credentials */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          background: "rgba(0,0,0,0.1)",
          padding: "2px 8px",
          borderRadius: "10px"
        }}>
          <Key size={10} />
          <code style={{ fontFamily: "monospace", fontSize: "10px" }}>test@test.com</code>
          <span style={{ opacity: 0.5 }}>|</span>
          <code style={{ fontFamily: "monospace", fontSize: "10px" }}>test123</code>
        </div>

        {/* Links */}
        <a
          href="http://dumontcloud-local.orb.local:8081/admin/doc/live"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "black", textDecoration: "none", fontSize: "10px" }}
        >
          Docs
        </a>
        <a
          href="http://dumontcloud-local.orb.local:8082/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "black", textDecoration: "none", fontSize: "10px" }}
        >
          Tests
        </a>
      </div>

      {/* Close button */}
      <button
        onClick={() => setIsVisible(false)}
        style={{
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: "2px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: 0.7
        }}
        title="Hide Dev Bar"
      >
        <X size={14} />
      </button>
    </div>
  );
};

export default DevBar;
