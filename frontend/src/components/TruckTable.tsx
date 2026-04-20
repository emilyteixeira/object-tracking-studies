import { TruckData } from "../types";

interface Props {
  trucks: TruckData[];
}

export default function TruckTable({ trucks }: Props) {
  return (
    <div className="space-y-2">
      <h2 className="text-white font-semibold text-sm uppercase tracking-wide">
        Caminhões ativos
      </h2>

      {trucks.length === 0 ? (
        <p className="text-gray-500 text-sm">Nenhum caminhão no ROI.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-3 py-2 text-left">ID</th>
                <th className="px-3 py-2 text-left">Placa</th>
                <th className="px-3 py-2 text-right">Vel. (km/h)</th>
                <th className="px-3 py-2 text-center">No ROI</th>
                <th className="px-3 py-2 text-center">Alerta</th>
              </tr>
            </thead>
            <tbody>
              {trucks.map((truck) => (
                <tr
                  key={truck.id}
                  className={`border-t border-gray-700 ${
                    truck.alert ? "bg-red-900/40" : "bg-gray-900"
                  }`}
                >
                  <td className="px-3 py-2 text-white font-mono">#{truck.id}</td>
                  <td className="px-3 py-2 font-mono tracking-widest">
                    {truck.license_plate ? (
                      <span className="text-yellow-300 font-bold">{truck.license_plate}</span>
                    ) : (
                      <span className="text-gray-600 text-xs">—</span>
                    )}
                  </td>
                  <td
                    className={`px-3 py-2 text-right font-bold ${
                      truck.speed_kmh >= 80
                        ? "text-red-400"
                        : truck.speed_kmh >= 60
                        ? "text-orange-400"
                        : "text-green-400"
                    }`}
                  >
                    {truck.speed_kmh.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {truck.in_roi ? (
                      <span className="text-green-400">✓</span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {truck.alert ? (
                      <span className="text-red-400 font-bold">⚠</span>
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
