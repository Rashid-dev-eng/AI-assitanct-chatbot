import type { AppPage } from '../../types/app';

interface SidebarProps {
  pages: readonly AppPage[];
  activePage: AppPage;
  onNavigate: (page: AppPage) => void;
  onLogout: () => void;
}

export function Sidebar({ pages, activePage, onNavigate, onLogout }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand"><span className="logo">DMI</span><span>DMI DeLMS</span></div>
      <nav className="nav" aria-label="Main navigation">
        {pages.map((item) => <button key={item} className={activePage === item ? 'active' : ''} onClick={() => onNavigate(item)}>{item}</button>)}
        <button onClick={onLogout}>Logout</button>
      </nav>
    </aside>
  );
}
