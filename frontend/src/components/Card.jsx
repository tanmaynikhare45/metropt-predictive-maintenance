export default function Card({ title, subtitle, right, loading, error, empty, emptyText, loadingText, className = '', children }) {
  let body = children
  if (loading) body = <div className="placeholder">{loadingText || 'Loading…'}</div>
  else if (empty) body = <div className="placeholder">{emptyText || 'No data'}</div>

  return (
    <section className={`card ${className}`}>
      <header className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
        {right && <div className="card-right">{right}</div>}
      </header>
      {error && <div className="banner error">{error}</div>}
      <div className="card-body">{body}</div>
    </section>
  )
}
