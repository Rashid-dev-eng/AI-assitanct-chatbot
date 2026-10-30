import { Dashboard } from './Dashboard';
import { CourseCards } from './CourseCards';
import type { AppPage } from '../types/app';

interface PageContentProps { page: AppPage; onOpenAssistant: () => void; onNavigate: (page: AppPage) => void }

export function PageContent({ page, onOpenAssistant, onNavigate }: PageContentProps) {
  if (page === 'Dashboard') return <Dashboard onNavigate={onNavigate} />;
  if (page === 'My Courses' || page === 'Course Catalogue') return <CourseCards />;
  if (page === 'Assignments') {
    return <section className="panel wide"><h3>Assignments</h3><p>Bridge Watchkeeping Reflection · Due 27 October · <b>Pending</b></p><p>Safety Case Study · Due 31 October · <b>Pending</b></p><label htmlFor="demo-submission">Demo text submission</label><input id="demo-submission" placeholder="Write your response" /><button className="primary" style={{ marginTop: 12 }}>Submit</button></section>;
  }
  if (page === 'AI Learning Assistant') {
    return <section className="panel wide"><h3>DMI Learning Assistant</h3><p>This page shares the floating assistant's local demonstration engine. Open it in the lower-right corner.</p><button className="primary" onClick={onOpenAssistant}>Open assistant</button></section>;
  }
  return <section className="panel wide"><h3>{page}</h3><p className="sub">This demonstration page is ready for local prototype content and interactions.</p><div className="notice">All information shown is fictional demonstration data.</div></section>;
}
