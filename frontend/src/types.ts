export interface TruckData {
  id: number;
  speed_kmh: number;
  bbox: [number, number, number, number];
  centroid: [number, number];
  in_roi: boolean;
  alert: boolean;
}

export interface Stats {
  total_seen: number;
  active_count: number;
  avg_speed_kmh: number;
  max_speed_kmh: number;
  min_speed_kmh: number;
  fps: number;
}

export interface AlertEvent {
  truck_id: number;
  speed_kmh: number;
  timestamp: number;
  threshold_kmh: number;
}

export interface ConfigData {
  speed_threshold_kmh: number;
  roi_y_min: number;
  roi_y_max: number;
  meters_per_pixel: number;
}

export interface FrameMessage {
  type: "frame";
  timestamp: number;
  frame: string;
  trucks: TruckData[];
  stats: Stats;
  alerts: AlertEvent[];
  config: ConfigData;
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected";
