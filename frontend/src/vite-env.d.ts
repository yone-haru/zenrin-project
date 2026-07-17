/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_ZENRIN_MAP_API_KEY?: string
  /** Maps JavaScript APIを有効化したGoogle Cloudのキー。未設定時はOSM/Leaflet地図で動作する（plan v3.2）。 */
  readonly VITE_GOOGLE_MAPS_API_KEY?: string
}
