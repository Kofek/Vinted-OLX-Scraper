import { useTranslation } from "react-i18next";

export default function Footer() {
  const { t } = useTranslation();

  return (
    <footer className="footer">
      <div>
        <strong>AetherScrape</strong>
        <p>© 2024 AetherScrape Systems</p>
      </div>

      <nav className="footer-links">
        <a href="#">{t("footer.documentation")}</a>
        <a href="#">{t("footer.apiReference")}</a>
        <a href="#">{t("footer.status")}</a>
        <a href="#">{t("footer.privacy")}</a>
      </nav>
    </footer>
  );
}