// @TASK P1-S0-T1 - Top navigation bar component
import { Link } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

export function TopBar() {
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
  };

  // User initials for avatar
  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'U';

  return (
    <header
      role="banner"
      className="fixed top-0 left-0 right-0 z-50 h-14 bg-neutral-900 border-b border-neutral-800 flex items-center px-4"
    >
      {/* Logo */}
      <div className="flex items-center gap-2 flex-1">
        <div className="w-7 h-7 bg-primary rounded flex items-center justify-center flex-shrink-0">
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4 text-white"
          >
            <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 14a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 5.677V19a1 1 0 11-2 0V5.677L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.616a1 1 0 01.894-1.79l1.599.8L9 4.323V3a1 1 0 011-1z" />
          </svg>
        </div>
        <span className="text-white font-semibold text-sm tracking-tight">
          Memory SCM
        </span>
      </div>

      {/* Right side actions */}
      <nav
        aria-label="Top navigation actions"
        className="flex items-center gap-1"
      >
        {/* Settings link */}
        <Link
          to="/settings/alerts"
          aria-label="Alert settings"
          className="w-9 h-9 flex items-center justify-center rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors duration-150"
        >
          {/* Gear icon */}
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-5 h-5"
          >
            <path
              fillRule="evenodd"
              d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
              clipRule="evenodd"
            />
          </svg>
        </Link>

        {/* User avatar / logout */}
        <button
          onClick={handleLogout}
          aria-label={`Logged in as ${user?.email ?? 'user'}. Click to logout.`}
          title="Logout"
          className="flex items-center gap-2 h-9 pl-1 pr-2 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors duration-150 ml-1"
        >
          <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
            {initials}
          </div>
          {user?.email && (
            <span className="text-xs text-neutral-300 max-w-32 truncate hidden sm:block">
              {user.email}
            </span>
          )}
        </button>
      </nav>
    </header>
  );
}
