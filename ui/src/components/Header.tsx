import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Search", end: true },
  { to: "/search-comparison", label: "Search Lab", end: false },
  { to: "/datasets", label: "Datasets", end: false },
  { to: "/providers", label: "LLM Providers", end: false },
  { to: "/ingestion-pipelines", label: "Pipelines", end: false },
  { to: "/pipeline-runs", label: "Indexing Runs", end: false },
];

const Header = () => {
  return (
    <header className="sticky top-0 z-30 bg-emd-background/85 backdrop-blur-md border-b border-white/10 shadow-lg shadow-black/20">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col items-center py-3">
        <NavLink
          to="/"
          className="cursor-pointer flex flex-row items-center gap-2 group"
        >
          <img
            src="logo-1.png"
            alt="Embeddorium logo"
            className="w-10 h-10 sm:w-16 sm:h-16 object-contain transition-transform duration-300 group-hover:scale-105"
          />
          <h1 className="font-display tracking-widest font-bold text-emd-primary uppercase text-2xl sm:text-4xl lg:text-5xl">
            Embeddorium
          </h1>
        </NavLink>

        <nav className="flex flex-wrap items-center justify-center gap-x-4 gap-y-3 sm:gap-x-7 mt-3">
          {navItems.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `relative whitespace-nowrap font-display uppercase tracking-widest text-sm sm:text-lg transition-colors duration-200 after:absolute after:left-0 after:-bottom-1.5 after:h-0.5 after:rounded-full after:bg-emd-primary after:transition-all after:duration-300 ${
                  isActive
                    ? "text-emd-primary after:w-full"
                    : "text-emd-panel/80 hover:text-emd-primary after:w-0 hover:after:w-full"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
};

export default Header;
