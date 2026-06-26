import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { API_BASE_URL, fetchReports } from '../api/reports'
import type { Report } from '../api/reports'
import { colorForRiskScore } from '../utils/riskColor'

const DEFAULT_CENTER: [number, number] = [35.681236, 139.767125]

interface MapViewProps {
  refreshToken: number
  selectedLocation?: { lat: number; lng: number } | null
  onLocationSelect?: (lat: number, lng: number) => void
}

function LocationPicker({ onLocationSelect }: { onLocationSelect?: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onLocationSelect?.(event.latlng.lat, event.latlng.lng)
    },
  })
  return null
}

export function MapView({ refreshToken, selectedLocation, onLocationSelect }: MapViewProps) {
  const [reports, setReports] = useState<Report[]>([])

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .catch(() => setReports([]))
  }, [refreshToken])

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={15} style={{ height: '500px', width: '100%' }}>
      {/* ゼンリン地図タイルAPIキー取得後、ここをゼンリン提供のタイルURLに差し替える */}
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <LocationPicker onLocationSelect={onLocationSelect} />
      {selectedLocation && (
        <CircleMarker
          center={[selectedLocation.lat, selectedLocation.lng]}
          radius={8}
          pathOptions={{ color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.9 }}
        >
          <Popup>投稿位置</Popup>
        </CircleMarker>
      )}
      {reports.map((report) => (
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
            {report.image_urls[0] && (
              <img
                src={`${API_BASE_URL}${report.image_urls[0]}`}
                alt="危険箇所の写真"
                style={{ width: '160px', display: 'block', marginBottom: '4px' }}
              />
            )}
            <p>危険度: {report.risk_score ?? '未算出'}</p>
            <p>{report.description_ai ?? '解析中'}</p>
            <p>{new Date(report.created_at).toLocaleString('ja-JP')}</p>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
