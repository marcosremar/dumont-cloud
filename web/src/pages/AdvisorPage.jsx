import GPUAdvisor from '../components/gpu-advisor/GPUAdvisor'

export default function AdvisorPage({ user, onLogout }) {
    const getAuthHeaders = () => {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
        return token ? { 'Authorization': `Bearer ${token}` } : {}
    }

    return <GPUAdvisor getAuthHeaders={getAuthHeaders} />
}

