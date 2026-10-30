import { courses, courseProgress } from '../data/courses';

export function CourseCards() {
  return <div className="grid">{courses.map((course, index) => <section className="panel" key={course}><h3>{course}</h3><p className="sub">MAR {101 + index} · Demo course</p><div className="bar"><i style={{ width: `${courseProgress[index]}%` }} /></div><p>{courseProgress[index]}% progress</p><button className="primary">Open course</button></section>)}</div>;
}
