interface DisclaimerBadgeProps {
  visible: boolean;
}

export function DisclaimerBadge({ visible }: DisclaimerBadgeProps) {
  if (!visible) return null;

  return (
    <div className="disclaimer-badge" role="status">
      <span className="disclaimer-mark" aria-hidden="true">
        <svg viewBox="0 0 16 16">
          <circle cx="8" cy="8" r="6" />
          <path d="M8 7.2v3.2M8 5.2v.4" />
        </svg>
      </span>
      Información educativa: no es asesoría financiera.
    </div>
  );
}
