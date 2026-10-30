interface LoginPageProps { onLogin: () => void }

export function LoginPage({ onLogin }: LoginPageProps) {
  return (
    <main className="login">
      <section className="login-card">
        <div className="brand"><span className="logo">DMI</span><span>DMI DeLMS</span></div>
        <h1>Welcome back</h1>
        <p className="sub">Sign in to the e-learning demonstration.</p>
        <label htmlFor="login-email">Email or username</label>
        <input id="login-email" defaultValue="student@demo.delms" autoComplete="username" />
        <label htmlFor="login-password">Password</label>
        <input id="login-password" type="password" defaultValue="demo123" autoComplete="current-password" />
        <button className="primary" style={{ width: '100%', marginTop: 14 }} onClick={onLogin}>Log in</button>
        <div className="demo"><b>Demo accounts</b><br />Student: student@demo.delms<br />Lecturer: lecturer@demo.delms<br />Administrator: admin@demo.delms<br />Password: demo123</div>
      </section>
    </main>
  );
}
