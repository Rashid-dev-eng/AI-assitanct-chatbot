import { Sidebar } from '../navigation/Sidebar';
import { Topbar } from '../navigation/Topbar';
import { PageContent } from '../../pages/PageContent';
import type { AppPage, UiLanguage } from '../../types/app';

interface AppLayoutProps {
  page: AppPage;
  pages: readonly AppPage[];
  language: UiLanguage;
  onNavigate: (page: AppPage) => void;
  onLanguageChange: (language: UiLanguage) => void;
  onLogout: () => void;
  onOpenAssistant: () => void;
}

export function AppLayout(props: AppLayoutProps) {
  return (
    <div className="app">
      <Sidebar pages={props.pages} activePage={props.page} onNavigate={props.onNavigate} onLogout={props.onLogout} />
      <main className="main">
        <Topbar page={props.page} language={props.language} onLanguageChange={props.onLanguageChange} />
        <div className="content"><PageContent page={props.page} onOpenAssistant={props.onOpenAssistant} onNavigate={props.onNavigate} /></div>
      </main>
    </div>
  );
}
