import { courses, courseProgress } from '../data/courses';
import type { AppPage } from '../types/app';

interface DashboardProps { onNavigate: (page: AppPage) => void }

export function Dashboard({ onNavigate }: DashboardProps) {
  return (
    <>
      <div className="notice">Demonstration data only — this prototype is not connected to official DMI records.</div>
      <div className="grid">
        <section className="panel wide">
          <h3>Welcome back, Asha</h3><p className="sub">Continue your maritime learning journey.</p>
          {courses.map((course, index) => <div className="course" key={course}><b>{course}</b><p>{courseProgress[index]}% complete</p><div className="bar"><i style={{ width: `${courseProgress[index]}%` }} /></div></div>)}
        </section>
        <section className="panel"><h3>Pending work</h3><div className="metric">3</div><p className="sub">Assignments due this week</p><button className="primary" onClick={() => onNavigate('Assignments')}>View assignments</button></section>
        <section className="panel"><h3>Upcoming quiz</h3><b>COLREG Regulations</b><p className="sub">Available until 28 October</p><button className="primary" onClick={() => onNavigate('Quizzes')}>Open quizzes</button></section>
      </div>
    </>
  );
}
