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
    if (!isNaN(num) && num > 0) {
      onSet(num);
    }
  };

  return (
    <div className="space-y-2">
      <h2 className="text-white font-semibold text-sm uppercase tracking-wide">
        Limite de velocidade
      </h2>
      <div className="bg-gray-800 rounded-lg p-3 space-y-2">
        <p className="text-gray-400 text-xs">
          Limite atual:{" "}
          <span className="text-yellow-400 font-bold">{currentThreshold} km/h</span>
        </p>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="number"
            min={1}
            max={300}
            step={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="flex-1 bg-gray-700 text-white rounded px-3 py-1.5 text-sm border border-gray-600 focus:outline-none focus:border-yellow-400"
            placeholder="km/h"
          />
          <button
            type="submit"
            className="bg-yellow-500 hover:bg-yellow-400 text-black font-semibold px-4 py-1.5 rounded text-sm transition-colors"
          >
            Aplicar
          </button>
        </form>
      </div>
    </div>
  );
}
