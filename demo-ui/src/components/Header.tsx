import gdgLogo from "../assets/gdg-logo.png";

import type { ChatMode, ClientUser } from "../types";
import { ModeSelect } from "./ModeSelect";

interface HeaderProps {
  user?: ClientUser | null;
  mode?: ChatMode;
  onModeChange?: (mode: ChatMode) => void;
}

export function Header({
  user = null,
  mode = "agent",
  onModeChange,
}: HeaderProps) {
  return (
    <header className="header">
      <div className="brand">
        <img
          className="brand-logo"
          src={gdgLogo}
          alt="Google Developer Groups"
          width="53"
          height="26"
        />
        <span className="brand-name">DevFest 2026</span>
      </div>

      {(onModeChange || user) && (
        <div className="header-actions">
          {onModeChange && <ModeSelect value={mode} onChange={onModeChange} />}
          {user && (
            <div className="header-user">
              <span className="header-user-initials" aria-hidden="true">
                {user.name
                  .split(/\s+/)
                  .filter(Boolean)
                  .map((part) => part[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </span>
              <span className="header-user-name">{user.name}</span>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
