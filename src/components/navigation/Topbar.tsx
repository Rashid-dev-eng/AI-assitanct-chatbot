import type { AppPage, UiLanguage } from '../../types/app';

interface TopbarProps {
  page: AppPage;
  language: UiLanguage;
  onLanguageChange: (language: UiLanguage) => void;
}

export function Topbar({ page, language, onLanguageChange }: TopbarProps) {
  return (
    <header className="topbar">
      <h2>{page}</h2>
      <div className="controls">
        <select aria-label="Demo role" defaultValue="Student"><option>Student</option><option>Lecturer</option><option>Administrator</option></select>
        <select aria-label="Language" value={language} onChange={(event) => onLanguageChange(event.target.value as UiLanguage)}>
          <option value="ENG">ENG</option><option value="SW">SW</option>
        </select>
      </div>
    </header>
  );
}
