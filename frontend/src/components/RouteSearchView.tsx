import { useState } from 'react'
import { geocode, searchRoute } from '../api/route'
import type { GeocodeResult, RouteSearchResult } from '../api/route'
import { RouteMap } from './RouteMap'

interface LocationState {
  query: string
  candidates: GeocodeResult[]
  selected: GeocodeResult | null
}

const EMPTY_LOCATION: LocationState = { query: '', candidates: [], selected: null }

type LocationTarget = 'origin' | 'destination'

export function RouteSearchView() {
  const [origin, setOrigin] = useState<LocationState>(EMPTY_LOCATION)
  const [destination, setDestination] = useState<LocationState>(EMPTY_LOCATION)
  const [result, setResult] = useState<RouteSearchResult | null>(null)
  const [status, setStatus] = useState<'idle' | 'searching' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  function setLocationState(target: LocationTarget, value: LocationState) {
    if (target === 'origin') {
      setOrigin(value)
    } else {
      setDestination(value)
    }
  }

  function handleQueryChange(target: LocationTarget, value: string) {
    const current = target === 'origin' ? origin : destination
    setLocationState(target, { query: value, candidates: current.candidates, selected: null })
  }

  async function handleGeocodeSearch(target: LocationTarget) {
    const current = target === 'origin' ? origin : destination
    try {
      const candidates = await geocode(current.query)
      setLocationState(target, { ...current, candidates })
    } catch {
      setStatus('error')
      setErrorMessage('地点検索に失敗しました')
    }
  }

  function handleSelectCandidate(target: LocationTarget, candidate: GeocodeResult) {
    setLocationState(target, { query: candidate.name, candidates: [], selected: candidate })
  }

  async function handleSearchRoute() {
    if (!origin.selected || !destination.selected) {
      setStatus('error')
      setErrorMessage('出発地と目的地を選択してください')
      return
    }

    setStatus('searching')
    try {
      const routeResult = await searchRoute({
        fromLat: origin.selected.latitude,
        fromLng: origin.selected.longitude,
        toLat: destination.selected.latitude,
        toLng: destination.selected.longitude,
      })
      setResult(routeResult)
      setStatus('idle')
    } catch (error) {
      setStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'ルート検索に失敗しました')
    }
  }

  return (
    <div>
      <h2>ルート検索</h2>

      <div>
        <label>
          出発地
          <input value={origin.query} onChange={(event) => handleQueryChange('origin', event.target.value)} />
        </label>
        <button type="button" onClick={() => handleGeocodeSearch('origin')}>
          検索
        </button>
        {origin.candidates.length > 0 && (
          <ul>
            {origin.candidates.map((candidate) => (
              <li key={`${candidate.latitude}-${candidate.longitude}`}>
                <button type="button" onClick={() => handleSelectCandidate('origin', candidate)}>
                  {candidate.name}
                </button>
              </li>
            ))}
          </ul>
        )}
        {origin.selected && <p>選択中: {origin.selected.name}</p>}
      </div>

      <div>
        <label>
          目的地
          <input
            value={destination.query}
            onChange={(event) => handleQueryChange('destination', event.target.value)}
          />
        </label>
        <button type="button" onClick={() => handleGeocodeSearch('destination')}>
          検索
        </button>
        {destination.candidates.length > 0 && (
          <ul>
            {destination.candidates.map((candidate) => (
              <li key={`${candidate.latitude}-${candidate.longitude}`}>
                <button type="button" onClick={() => handleSelectCandidate('destination', candidate)}>
                  {candidate.name}
                </button>
              </li>
            ))}
          </ul>
        )}
        {destination.selected && <p>選択中: {destination.selected.name}</p>}
      </div>

      <button type="button" onClick={handleSearchRoute} disabled={status === 'searching'}>
        {status === 'searching' ? '検索中...' : 'ルートを検索'}
      </button>

      {status === 'error' && <p role="alert">{errorMessage}</p>}

      {result && origin.selected && destination.selected && (
        <>
          <RouteMap
            origin={{ lat: origin.selected.latitude, lng: origin.selected.longitude }}
            destination={{ lat: destination.selected.latitude, lng: destination.selected.longitude }}
            result={result}
          />
          <h3>ルート上の危険地点（{result.danger_reports.length}件）</h3>
          <ul>
            {result.danger_reports.map(({ report, distance_from_route_m }) => (
              <li key={report.id}>
                危険度{report.risk_score ?? '未算出'} / {report.description_ai ?? '解析中'}
                （ルートから約{Math.round(distance_from_route_m)}m）
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
