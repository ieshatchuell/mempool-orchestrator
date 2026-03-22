"use client";

import { createContext, useState, type ReactNode } from "react";
import { en, type Dictionary } from "./en";
import { es } from "./es";

/**
 * Supported locales for the dashboard UI.
 */
export type Locale = "en" | "es";

/**
 * Context value shape — provides the current locale, dictionary, and setter.
 */
export interface I18nContextValue {
  locale: Locale;
  t: Dictionary;
  setLocale: (locale: Locale) => void;
}

const dictionaries: Record<Locale, Dictionary> = { en, es };

export const I18nContext = createContext<I18nContextValue>({
  locale: "en",
  t: en,
  setLocale: () => {},
});

/**
 * Lightweight i18n provider using React Context API only.
 *
 * Wraps the app and exposes `locale`, `t` (the active dictionary),
 * and `setLocale` to all children via `useTranslations()`.
 *
 * No external i18n library required — pure React state.
 */
export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  return (
    <I18nContext.Provider value={{ locale, t: dictionaries[locale], setLocale }}>
      {children}
    </I18nContext.Provider>
  );
}
