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
          waiting: "Oczekujący",
          paused: "Wstrzymany",
          error: "Błąd",
          unknown: "Nieznany",
        },
        actions: {
          pause: "Pauza",
          resume: "Wznów",
          toggling: "…",
          toggleError: "Nie udało się zmienić statusu bota.",
          editAria: "Edytuj bota",
        },
        pagination: {
          prev: "Poprzednia",
          next: "Następna",
          page: "Strona {{current}} z {{total}}",
          navAria: "Paginacja listy botów",
        },
        create: {
          openButton: "Dodaj bota",
          title: "Nowy bot",
          closeAria: "Zamknij okno tworzenia bota",
          name: "Nazwa",
          source: "Źródło",
          sourceMixed: "OLX + Vinted",
          sourceOlx: "OLX",
          sourceVinted: "Vinted",
          urlsOlx: "Linki OLX",
          urlsVinted: "Linki Vinted",
          addUrl: "Dodaj link",
          removeUrlAria: "Usuń ten link",
          urlPlaceholder: "https://…",
          webhookUrl: "Webhook URL",
          promptText: "Tekst promptu",
          enabled: "Bot włączony",
          cancel: "Anuluj",
          submit: "Utwórz bota",
          submitting: "Tworzenie…",
          errorGeneric: "Nie udało się utworzyć bota.",
        },
        edit: {
          title: "Edytuj bota",
          closeAria: "Zamknij okno edycji bota",
          botId: "ID",
          submit: "Zapisz zmiany",
          submitting: "Zapisywanie…",
          delete: "Usuń bota",
          deleting: "Usuwanie…",
          deleteConfirm: "Na pewno usunąć bota „{{name}}”? Tej operacji nie cofniesz.",
          deleteError: "Nie udało się usunąć bota.",
          errorGeneric: "Nie udało się zapisać zmian.",
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
          waiting: "Waiting",
          paused: "Paused",
          error: "Error",
          unknown: "Unknown",
        },
        actions: {
          pause: "Pause",
          resume: "Resume",
          toggling: "…",
          toggleError: "Could not change bot status.",
          editAria: "Edit bot",
        },
        pagination: {
          prev: "Previous",
          next: "Next",
          page: "Page {{current}} / {{total}}",
          navAria: "Bot list pagination",
        },
        create: {
          openButton: "Add bot",
          title: "New bot",
          closeAria: "Close create bot dialog",
          name: "Name",
          source: "Source",
          sourceMixed: "OLX + Vinted",
          sourceOlx: "OLX",
          sourceVinted: "Vinted",
          urlsOlx: "OLX links",
          urlsVinted: "Vinted links",
          addUrl: "Add link",
          removeUrlAria: "Remove this link",
          urlPlaceholder: "https://…",
          webhookUrl: "Webhook URL",
          promptText: "Prompt text",
          enabled: "Bot enabled",
          cancel: "Cancel",
          submit: "Create bot",
          submitting: "Creating…",
          errorGeneric: "Could not create the bot.",
        },
        edit: {
          title: "Edit bot",
          closeAria: "Close edit bot dialog",
          botId: "ID",
          submit: "Save changes",
          submitting: "Saving…",
          delete: "Delete bot",
          deleting: "Deleting…",
          deleteConfirm: "Delete bot “{{name}}”? This cannot be undone.",
          deleteError: "Could not delete the bot.",
          errorGeneric: "Could not save changes.",
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