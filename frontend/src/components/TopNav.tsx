import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function TopNav() {
  const { t, i18n } = useTranslation();

  return (
    <header className="topnav">
      <div className="brand">AetherScrape</div>

      <nav className="menu">
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : "")}>
          {t("nav.dashboard")}
        </NavLink>
        <NavLink to="/my-bots" className={({ isActive }) => (isActive ? "active" : "")}>
          {t("nav.myBots")}
        </NavLink>
        <a href="#">{t("nav.analytics")}</a>
        <a href="#">{t("nav.settings")}</a>
      </nav>

      <div style={{ display: "flex", gap: 8 }}>
        <button className="deploy-btn" onClick={() => i18n.changeLanguage("pl")}>
          {t("lang.pl")}
        </button>
        <button className="deploy-btn" onClick={() => i18n.changeLanguage("en")}>
          {t("lang.en")}
        </button>
      </div>
    </header>
  );
}