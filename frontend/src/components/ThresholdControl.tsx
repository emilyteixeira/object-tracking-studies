import { useState } from "react";

interface Props {
  currentThreshold: number;
  onSet: (kmh: number) => void;
}

export default function ThresholdControl({ currentThreshold, onSet }: Props) {
  const [value, setValue] = useState<string>(String(currentThreshold));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const num = parseFloat(value);
    if (!isNaN(num) && num > 0) onSet(num);
  };

  return (
    <div className="ds-card">
      <div className="ds-card-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
        </svg>
        Limite de velocidade
      </div>

      <div className="threshold-display">
        <span className="thr-lbl">Limite atual</span>
        <span className="thr-val">
          {currentThreshold}
          <span className="thr-unit" style={{ marginLeft: 4 }}>km/h</span>
        </span>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8 }}>
        <input
          type="number"
          min={1}
          max={300}
          step={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="km/h"
          style={{
            flex: 1, minWidth: 0,
            background: "rgba(0,0,0,0.35)",
            border: "1px solid var(--bg3)",
            borderRadius: 8, padding: "9px 12px",
            color: "var(--fg1)",
            fontFamily: "var(--font-mono)",
            fontSize: 14, outline: "none",
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "var(--accent-primary)";
            e.target.style.boxShadow = "0 0 0 3px var(--accent-ring)";
          }}
          onBlur={(e) => {
            e.target.style.borderColor = "var(--bg3)";
            e.target.style.boxShadow = "none";
          }}
        />
        <button type="submit" className="btn-primary">Aplicar</button>
      </form>
    </div>
  );
}
