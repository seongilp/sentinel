export interface UserRow {
  id: number
  username: string
  email: string
  role: string
  status: string
  last_login: string
  created_at: string
}

export interface UserAuditEvent {
  localId: string
  action: 'user.locked' | 'user.unlocked'
  username: string
  by: string
  created_at: string
}

export const LOCK_DAYS = 90

const INITIAL_USERS: UserRow[] = [
  { id: 1, username: 'admin',     email: 'admin@sentinel.internal',     role: 'admin',   status: 'active',   last_login: '2026-03-22T03:00:00', created_at: '2025-01-01' },
  { id: 2, username: 'analyst01', email: 'analyst01@sentinel.internal', role: 'analyst', status: 'active',   last_login: '2026-03-21T18:30:00', created_at: '2025-03-15' },
  { id: 3, username: 'viewer01',  email: 'viewer01@sentinel.internal',  role: 'viewer',  status: 'active',   last_login: '2026-03-20T10:15:00', created_at: '2025-06-01' },
  { id: 4, username: 'analyst02', email: 'analyst02@sentinel.internal', role: 'analyst', status: 'inactive', last_login: '2025-10-15T09:00:00', created_at: '2025-07-20' },
  { id: 5, username: 'viewer02',  email: 'viewer02@sentinel.internal',  role: 'viewer',  status: 'active',   last_login: '2026-03-22T01:00:00', created_at: '2025-09-10' },
  { id: 6, username: 'viewer03',  email: 'viewer03@sentinel.internal',  role: 'viewer',  status: 'active',   last_login: '2025-08-01T14:30:00', created_at: '2025-07-01' },
  { id: 7, username: 'analyst03', email: 'analyst03@sentinel.internal', role: 'analyst', status: 'active',   last_login: '2025-11-20T11:00:00', created_at: '2025-10-01' },
]

export function useUsers() {
  const users = useState<UserRow[]>('sentinel:users', () => INITIAL_USERS)
  const manuallyUnlocked = useState<number[]>('sentinel:unlocked', () => [])
  const manuallyLocked = useState<number[]>('sentinel:locked', () => [])
  const userAuditEvents = useState<UserAuditEvent[]>('sentinel:userAudit', () => [])
  const auditInitialized = useState<boolean>('sentinel:auditInit', () => false)

  const now = new Date()

  function daysSinceLogin(last_login: string): number {
    return Math.floor((now.getTime() - new Date(last_login).getTime()) / (1000 * 60 * 60 * 24))
  }

  function isLocked(user: UserRow): boolean {
    if (manuallyLocked.value.includes(user.id)) return true
    if (manuallyUnlocked.value.includes(user.id)) return false
    return daysSinceLogin(user.last_login) > LOCK_DAYS
  }

  function initLockedEvents() {
    if (auditInitialized.value) return
    auditInitialized.value = true
    const events: UserAuditEvent[] = []
    users.value.forEach(user => {
      if (isLocked(user)) {
        const lockDate = new Date(new Date(user.last_login).getTime() + LOCK_DAYS * 24 * 60 * 60 * 1000)
        events.push({
          localId: `lock-${user.id}`,
          action: 'user.locked',
          username: user.username,
          by: 'system',
          created_at: lockDate.toISOString(),
        })
      }
    })
    userAuditEvents.value = events
  }

  function unlock(user: UserRow) {
    manuallyUnlocked.value = [...manuallyUnlocked.value, user.id]
    manuallyLocked.value = manuallyLocked.value.filter(id => id !== user.id)
    // Set status to active immediately
    users.value = users.value.map(u =>
      u.id === user.id ? { ...u, status: 'active', last_login: new Date().toISOString() } : u
    )
    userAuditEvents.value = [
      ...userAuditEvents.value,
      {
        localId: `unlock-${user.id}-${Date.now()}`,
        action: 'user.unlocked',
        username: user.username,
        by: 'admin',
        created_at: new Date().toISOString(),
      },
    ]
  }

  function lock(user: UserRow) {
    manuallyLocked.value = [...manuallyLocked.value, user.id]
    manuallyUnlocked.value = manuallyUnlocked.value.filter(id => id !== user.id)
    users.value = users.value.map(u =>
      u.id === user.id ? { ...u, status: 'inactive' } : u
    )
    userAuditEvents.value = [
      ...userAuditEvents.value,
      {
        localId: `lock-${user.id}-${Date.now()}`,
        action: 'user.locked',
        username: user.username,
        by: 'admin',
        created_at: new Date().toISOString(),
      },
    ]
  }

  const lockedUsers = computed(() => users.value.filter(u => isLocked(u)))
  const activeUsers = computed(() => users.value.filter(u => !isLocked(u) && u.status === 'active'))
  const inactiveUsers = computed(() => users.value.filter(u => !isLocked(u) && u.status === 'inactive'))

  return {
    users,
    userAuditEvents,
    isLocked,
    unlock,
    lock,
    initLockedEvents,
    daysSinceLogin,
    lockedUsers,
    activeUsers,
    inactiveUsers,
    LOCK_DAYS,
  }
}
