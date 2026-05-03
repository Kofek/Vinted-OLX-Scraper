import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";


const resources = {
  pl: {
    common: {
      nav: {
        dashboard: "Dashboard",
        myBots: "Moje Boty",
        analytics: "Analityka",
        settings: "Ustawienia",
      },
      page: {
        dashboardTitle: "Dashboard",
        dashboardDesc: "To jest placeholder strony Dashboard.",
        myBotsTitle: "Moje Boty",
        eyebrow: "Panel Kontrolny",
        myBotsDesc: "Monitoruj swoje boty i zarządzaj nimi.",

      },
      myBots: {
        fetch: {
          loading: "Ładowanie listy botów…",
          ok: "Połączono. Widocznych botów na tej stronie: {{count}}.",
          error: "Brak połączenia z backendem. Uruchom API (FastAPI) i sprawdź endpoint /api/bots.",
        },
        empty: "Brak botów do wyświetlenia.",
        labels: {
          lastActivity: "Ostatnia aktywność",
          itemsFound: "Znalezione pozycje",
          successRate: "Skuteczność",
        },
        status: {
          running: "Aktywny",
          paused: "Wstrzymany",
        },
        actions: {
          pause: "Pauza",
          resume: "Wznów",
          editAria: "Edytuj bota",
        },
        pagination: {
          prev: "Poprzednia",
          next: "Następna",
          page: "Strona {{current}} z {{total}}",
        },
      },
      stats:{
        activeCount: "Aktywne boty",
        totalItems: "Przedmioty łącznie",
      },
      time: {
        justNow: "Przed chwilą",
      },
      footer: {
        documentation: "Dokumentacja",
        apiReference: "API Reference",
        status: "Status",
        privacy: "Prywatność",
      },
      lang: {
        pl: "PL",
        en: "EN",
      },
    },
  },
  en: {
    common: {
      nav: {
        dashboard: "Dashboard",
        myBots: "My Bots",
        analytics: "Analytics",
        settings: "Settings",
      },
      page: {
        dashboardTitle: "Dashboard",
        dashboardDesc: "This is a Dashboard placeholder page.",
        myBotsTitle: "My Bots",
        eyebrow: "Dashboard",
        myBotsDesc: "Monitor your bots and manage them.",
      },
      myBots: {
        fetch: {
          loading: "Loading bots…",
          ok: "Connected. Showing {{count}} bots on this page.",
          error: "Backend unavailable. Start the API (FastAPI) and check /api/bots.",
        },
        empty: "No bots to display.",
        labels: {
          lastActivity: "Last Activity",
          itemsFound: "Items Found",
          successRate: "Success Rate",
        },
        status: {
          running: "Running",
          paused: "Paused",
        },
        actions: {
          pause: "Pause",
          resume: "Resume",
          editAria: "Edit bot",
        },
        pagination: {
          prev: "Previous",
          next: "Next",
          page: "Page {{current}} / {{total}}",
        },
      },
      stats: {
        activeCount: "Active bots",
        totalItems: "Total items",
      },
      time: {
        justNow: "Just now",
      },
      footer: {
        documentation: "Documentation",
        apiReference: "API Reference",
        status: "Status",
        privacy: "Privacy",
      },
      lang: {
        pl: "PL",
        en: "EN",
      },
    },
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "pl",
    defaultNS: "common",
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
  });

export default i18n;