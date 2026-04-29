import { useTranslation } from "react-i18next";

export default function DashboardPage() {
  const { t } = useTranslation();

  return (
    <section style={{ padding: 20 }}>
      <h2>{t("page.dashboardTitle")}</h2>
      <p>{t("page.dashboardDesc")}</p>
    </section>
  );
}