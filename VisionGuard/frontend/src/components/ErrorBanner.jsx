export default function ErrorBanner({ error, onDismiss, onRetry }) {
  if (!error) return null;
  const hints = {
    BACKEND_UNREACHABLE: "Start the backend with start_backend.bat (or start_all.bat), wait for “Application startup complete”, then try again.",
    ULTRALYTICS_MISSING: "In the backend folder run: pip install -r requirements.txt",
  };
  return (
    <div className="error" role="alert">
      <div>
        <strong>{error.title}</strong>
        <p>{error.detail}</p>
        {hints[error.code] && <p className="hint">{hints[error.code]}</p>}
      </div>
      <div className="error-actions">
        {onRetry && <button className="btn btn-small" onClick={onRetry}>Try again</button>}
        <button className="btn btn-small" onClick={onDismiss}>Dismiss</button>
      </div>
    </div>
  );
}
