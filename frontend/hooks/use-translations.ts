import { useContext } from "react";
import { I18nContext } from "@/lib/i18n/context";

/**
 * Custom hook to access the i18n context.
 *
 * Returns `{ locale, t, setLocale }` where:
 * - `locale` is the current language ("en" | "es")
 * - `t` is the active dictionary object
 * - `setLocale` switches the language
 *
 * Usage:
 *   const { t, locale, setLocale } = useTranslations();
 *   <span>{t.header.title}</span>
 */
export function useTranslations() {
  return useContext(I18nContext);
}
