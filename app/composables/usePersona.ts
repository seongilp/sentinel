export type Role = 'admin' | 'analyst' | 'viewer'

export const ROLE_CONFIG: Record<Role, { label: string; color: string; bg: string; description: string }> = {
  admin:   { label: 'Admin',   color: '#7c3aed', bg: '#7c3aed20', description: '전체 권한' },
  analyst: { label: 'Analyst', color: '#2563eb', bg: '#2563eb20', description: '스캔·규칙 편집' },
  viewer:  { label: 'Viewer',  color: '#6b7280', bg: '#6b728020', description: '읽기 전용' },
}

// Menus hidden entirely per role (none hidden currently — all roles see all menus)
export const ROLE_WRITE_MENUS: Record<Role, string[]> = {
  admin:   ['dashboard','connections','scans','rules','classification','reports','deep-inspect','audit-log','users','settings'],
  analyst: ['scans','rules'],
  viewer:  [],
}

export function usePersona() {
  const persona = useState<Role>('sentinel:persona', () => 'admin')
  const isPersonaMode = computed(() => persona.value !== 'admin')

  function enterPersona(role: Role) {
    persona.value = role
  }

  function exitPersona() {
    persona.value = 'admin'
  }

  function canWrite(menuKey: string): boolean {
    return ROLE_WRITE_MENUS[persona.value].includes(menuKey)
  }

  return { persona, isPersonaMode, enterPersona, exitPersona, canWrite, ROLE_CONFIG }
}
