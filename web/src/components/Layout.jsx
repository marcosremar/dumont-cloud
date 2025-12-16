import { NavLink } from 'react-router-dom'

export default function Layout({ user, onLogout, children }) {
  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          <h1 className="logo">Dumont Cloud</h1>
          <nav className="nav">
            <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Dashboard
            </NavLink>
            <NavLink to="/machines" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Machines
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              Settings
            </NavLink>
          </nav>
        </div>
        <div className="header-right">
          <span className="user-name">{user?.username}</span>
          <button className="btn btn-sm" onClick={onLogout}>Logout</button>
        </div>
      </header>
      <main className="main">
        {children}
      </main>
    </div>
  )
}
