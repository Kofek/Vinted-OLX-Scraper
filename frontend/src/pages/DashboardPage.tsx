import { useTranslation } from "react-i18next";
import "./DashboardPage.css";

export default function DashboardPage() {
  const { t } = useTranslation();

  return (
    <section className="dashboard-page">
      <div className="dashboard-page__header">
        <p className="dashboard-page__eyebrow">{t("page.dashboardEyebrow")}</p>
        <h1 className="dashboard-page__title">{t("page.dashboardTitle")}</h1>
        <p className="dashboard-page__desc">{t("page.dashboardDesc")}</p>
      </div>
    </section>
  );
}
