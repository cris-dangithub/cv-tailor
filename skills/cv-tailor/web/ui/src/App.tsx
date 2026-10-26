import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { useEffect, useRef } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Shell } from "./components/Shell";
import { I18nProvider, pickLang, useI18n } from "./i18n";
import { api } from "./lib/api";
import { connectLive, notify } from "./lib/live";
import type { Thread } from "./lib/types";
import { ApplicationDetail } from "./pages/ApplicationDetail";
import { Applications } from "./pages/Applications";
import { Chat } from "./pages/Chat";
import { Desk } from "./pages/Desk";
import { Documents } from "./pages/Documents";
import { Settings } from "./pages/Settings";
import { Styles } from "./pages/Styles";

const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [
      { path: "/", element: <Desk /> },
      { path: "/applications", element: <Applications /> },
      { path: "/applications/:id", element: <ApplicationDetail /> },
      { path: "/documents", element: <Documents /> },
      { path: "/chat", element: <Chat /> },
      { path: "/chat/:tid", element: <Chat /> },
      { path: "/styles", element: <Styles /> },
      { path: "/settings", element: <Settings /> },
      { path: "*", element: <Desk /> },
    ],
  },
]);

function Live() {
  const qc = useQueryClient();
  const { t } = useI18n();
  const tRef = useRef(t);
  tRef.current = t;

  useEffect(
    () =>
      connectLive(qc, (th: Thread, before?: Thread) => {
        if (!before || before.status === th.status) return;
        const href = `/chat/${th.id}`;
        if (th.status === "idle" && before.status === "running") notify(tRef.current("notice.ready", { title: th.title }), href);
        if (th.status === "waiting") notify(tRef.current("notice.waiting", { title: th.title }), href);
        if (th.status === "error") notify(tRef.current("notice.failed", { title: th.title }), href);
      }),
    [qc],
  );
  return null;
}

export function App() {
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const lang = pickLang(settings.data?.ui_language, ws.data?.ui_language, navigator.language);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  return (
    <I18nProvider lang={lang}>
      <MotionConfig reducedMotion="user">
        <Live />
        <RouterProvider router={router} />
      </MotionConfig>
    </I18nProvider>
  );
}
