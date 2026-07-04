import { useId, useState } from 'react'
import type { KeyboardEvent } from 'react'
import type { GeocodeResult } from '../api/route'
import type { Target } from '../types'
import { Icon } from './Icon'

interface AddressFieldProps {
  label: string
  dotClassName: string
  value: string
  placeholder: string
  suggestions: GeocodeResult[]
  loading: boolean
  onChange: (value: string) => void
  onSelect: (result: GeocodeResult) => void
  onClose: () => void
  isActivePick: boolean
  onActivatePick: () => void
  pickButtonLabel: string
}

function AddressField({
  label,
  dotClassName,
  value,
  placeholder,
  suggestions,
  loading,
  onChange,
  onSelect,
  onClose,
  isActivePick,
  onActivatePick,
  pickButtonLabel,
}: AddressFieldProps) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const [trackedSuggestions, setTrackedSuggestions] = useState(suggestions)
  const inputId = useId()
  const listboxId = `${inputId}-listbox`

  // サジェスト候補が入れ替わったら選択インデックスをリセットする（レンダー中にstateを調整する公式パターン）。
  if (suggestions !== trackedSuggestions) {
    setTrackedSuggestions(suggestions)
    setActiveIndex(-1)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setOpen(false)
      onClose()
      return
    }
    if (!open || suggestions.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => (index + 1) % suggestions.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => (index - 1 + suggestions.length) % suggestions.length)
    } else if (event.key === 'Enter') {
      if (activeIndex >= 0) {
        event.preventDefault()
        onSelect(suggestions[activeIndex])
        setOpen(false)
      }
    }
  }

  return (
    <label className="address-field">
      <span>
        {label}
        {isActivePick && <em className="pick-flag">地図で指定中</em>}
      </span>
      <div className={`input-shell ${dotClassName}`}>
        <input
          id={inputId}
          type="text"
          role="combobox"
          aria-expanded={open && suggestions.length > 0}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-label={label}
          autoComplete="off"
          value={value}
          placeholder={placeholder}
          onChange={(event) => {
            onChange(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            window.setTimeout(() => setOpen(false), 120)
          }}
          onKeyDown={handleKeyDown}
        />
        {loading && <span className="field-spinner" aria-hidden="true" />}
        <button
          type="button"
          className={`map-pick-button ${isActivePick ? 'is-active' : ''}`}
          aria-pressed={isActivePick}
          aria-label={pickButtonLabel}
          title={pickButtonLabel}
          onClick={onActivatePick}
        >
          <Icon name="pin" />
        </button>
      </div>
      {open && suggestions.length > 0 && (
        <ul className="suggestion-list" id={listboxId} role="listbox">
          {suggestions.map((item, index) => (
            <li key={`${item.lat}-${item.lng}-${item.name}`} role="option" aria-selected={index === activeIndex}>
              <button
                type="button"
                className={index === activeIndex ? 'is-active' : ''}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onSelect(item)
                  setOpen(false)
                }}
              >
                {item.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </label>
  )
}

interface SearchPanelProps {
  originText: string
  destinationText: string
  onOriginTextChange: (value: string) => void
  onDestinationTextChange: (value: string) => void
  originSuggestions: GeocodeResult[]
  destinationSuggestions: GeocodeResult[]
  originSuggestLoading: boolean
  destinationSuggestLoading: boolean
  onSelectOrigin: (result: GeocodeResult) => void
  onSelectDestination: (result: GeocodeResult) => void
  onClearOriginSuggestions: () => void
  onClearDestinationSuggestions: () => void
  onSwap: () => void
  onSearch: () => void
  searching: boolean
  pickMode: Target
  onSetPickMode: (target: Target) => void
  isReporting: boolean
  onToggleReporting: () => void
}

export function SearchPanel({
  originText,
  destinationText,
  onOriginTextChange,
  onDestinationTextChange,
  originSuggestions,
  destinationSuggestions,
  originSuggestLoading,
  destinationSuggestLoading,
  onSelectOrigin,
  onSelectDestination,
  onClearOriginSuggestions,
  onClearDestinationSuggestions,
  onSwap,
  onSearch,
  searching,
  pickMode,
  onSetPickMode,
  isReporting,
  onToggleReporting,
}: SearchPanelProps) {
  return (
    <section className="search-card">
      <header className="brand-row">
        <span className="brand-icon">
          <Icon name="shield" />
        </span>
        <h1>通学路安全マップ</h1>
        <button
          type="button"
          className={`report-toggle ${isReporting ? 'is-active' : ''}`}
          aria-pressed={isReporting}
          onClick={onToggleReporting}
        >
          <Icon name="camera" />
          危険箇所を報告
        </button>
      </header>

      <div className={`pick-mode-banner ${isReporting ? 'is-disabled' : ''}`} role="status">
        <span>地図クリックで指定:</span>
        <div className="pick-mode-switch">
          <button
            type="button"
            aria-pressed={pickMode === 'origin'}
            disabled={isReporting}
            onClick={() => onSetPickMode('origin')}
          >
            出発地
          </button>
          <button
            type="button"
            aria-pressed={pickMode === 'destination'}
            disabled={isReporting}
            onClick={() => onSetPickMode('destination')}
          >
            目的地
          </button>
        </div>
      </div>

      <div className="field-stack">
        <AddressField
          label="出発地"
          dotClassName="origin-dot"
          value={originText}
          placeholder="出発地を入力"
          suggestions={originSuggestions}
          loading={originSuggestLoading}
          onChange={onOriginTextChange}
          onSelect={onSelectOrigin}
          onClose={onClearOriginSuggestions}
          isActivePick={!isReporting && pickMode === 'origin'}
          onActivatePick={() => onSetPickMode('origin')}
          pickButtonLabel="地図で出発地を指定"
        />
        <button className="swap-button" type="button" aria-label="出発地と目的地を入れ替え" onClick={onSwap}>
          <Icon name="swap" />
        </button>
        <AddressField
          label="目的地"
          dotClassName="destination-pin"
          value={destinationText}
          placeholder="目的地を入力"
          suggestions={destinationSuggestions}
          loading={destinationSuggestLoading}
          onChange={onDestinationTextChange}
          onSelect={onSelectDestination}
          onClose={onClearDestinationSuggestions}
          isActivePick={!isReporting && pickMode === 'destination'}
          onActivatePick={() => onSetPickMode('destination')}
          pickButtonLabel="地図で目的地を指定"
        />
      </div>

      <button
        className="search-button"
        type="button"
        onClick={onSearch}
        disabled={searching}
        aria-busy={searching}
      >
        {searching ? <span className="spinner" aria-hidden="true" /> : <Icon name="search" />}
        {searching ? '検索中...' : 'ルートを検索'}
      </button>
    </section>
  )
}
