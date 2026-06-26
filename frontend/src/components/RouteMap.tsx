import { CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { RouteSearchResult } from '../api/route'
import { colorForRiskScore } from '../utils/riskColor'

interface RouteMapProps {
  origin: { lat: number; lng: number }
  destination: { lat: number; lng: number }
  result: RouteSearchResult
}

export function RouteMap({ origin, destination, result }: RouteMapProps) {
  const positions: [number, number][] = result.route.points.map((point) => [
    point.latitude,
    point.longitude,
  ])
  const center = positions[Math.floor(positions.length / 2)] ?? [origin.lat, origin.lng]

  return (
    <MapContainer center={center} zoom={15} style={{ height: '500px', width: '100%' }}>
      {/* ゼンリン地図タイルAPIキー取得後、ここをゼンリン提供のタイルURLに差し替える */}
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline positions={positions} pathOptions={{ color: '#2563eb', weight: 5 }} />

      <CircleMarker
        center={[origin.lat, origin.lng]}
        radius={8}
        pathOptions={{ color: '#16a34a', fillColor: '#16a34a', fillOpacity: 1 }}
      >
        <Popup>出発地</Popup>
      </CircleMarker>
      <CircleMarker
        center={[destination.lat, destination.lng]}
        radius={8}
        pathOptions={{ color: '#dc2626', fillColor: '#dc2626', fillOpacity: 1 }}
      >
        <Popup>目的地</Popup>
      </CircleMarker>

      {result.danger_reports.map(({ report, distance_from_route_m }) => (
        <CircleMarker
          key={report.id}
          center={[report.latitude, report.longitude]}
          radius={10}
          pathOptions={{
            color: colorForRiskScore(report.risk_score),
            fillColor: colorForRiskScore(report.risk_score),
            fillOpacity: 0.8,
          }}
        >
          <Popup>
            <p>危険度: {report.risk_score ?? '未算出'}</p>
            <p>{report.description_ai ?? '解析中'}</p>
            <p>ルートから約{Math.round(distance_from_route_m)}m</p>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
