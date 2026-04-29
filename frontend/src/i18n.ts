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
      stats:{
        activeCount: "LICZNIK AKTYWNYCH BOTÓW",
        totalItems: "ŁĄCZNA LICZBA ZNALEZIONYCH PRZEDMIOTÓW"
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
      stats:{
        activeCount: "ACTIVE BOTS COUNT",
        totalItems: "TOTAL ITEMS FOUND"

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