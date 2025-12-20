import SavingsDashboard from '../components/savings/SavingsDashboard'

export default function SavingsPage({ user, onLogout }) {
    const getAuthHeaders = () => {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
        return token ? { 'Authorization': `Bearer ${token}` } : {}
    }

    return <SavingsDashboard getAuthHeaders={getAuthHeaders} />
}

