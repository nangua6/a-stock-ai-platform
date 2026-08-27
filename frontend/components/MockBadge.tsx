import { isMockData } from '@/lib/utils'

/**
 * Badge that shows MOCK when data is from mock provider.
 */
export function MockBadge({ source }: { source?: string }) {
  if (!source || !isMockData(source)) return null
  return <span className="mock-badge ml-1">MOCK</span>
}
