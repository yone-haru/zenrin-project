/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_ZENRIN_MAP_API_KEY?: string
  /** Maps JavaScript APIを有効化したGoogle Cloudのキー。未設定時はOSM/Leaflet地図で動作する（plan v3.2）。 */
  readonly VITE_GOOGLE_MAPS_API_KEY?: string
  /** Cloud Consoleで作成したMap ID。未設定時はデモID(DEMO_MAP_ID)で描画する。 */
  readonly VITE_GOOGLE_MAPS_MAP_ID?: string
  /** 「このマップについて」モーダルの問い合わせ先メール。未設定時はmailtoリンクを表示しない（plan v3.3）。 */
  readonly VITE_CONTACT_EMAIL?: string
}
