import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { useEffect, useRef } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Shell } from "./components/Shell";
import { I18nProvider, pickLang, useI18n } from "./i18n";
import { api, UNAUTHORIZED } from "./lib/api";
import { connectLive, notify } from "./lib/live";
import type { Thread } from "./lib/types";
import { ApplicationDetail } from "./pages/ApplicationDetail";
import { Applications } from "./pages/Applications";
import { Chat } from "./pages/Chat";
import { Desk } from "./pages/Desk";
import { Documents } from "./pages/Documents";
import { Login } from "./pages/Login";
import { Settings } from "./pages/Settings";
import { Styles } from "./pages/Styles";
import { Users } from "./pages/Users";

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
      { path: "/users", element: <Users /> },
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
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false, staleTime: 60_000 });
  const signedIn = !!me.data && !me.isError;
  const ws = useQuery({ queryKey: ["workspace"], queryFn: api.workspace, enabled: signedIn });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings, enabled: signedIn });
  const lang = pickLang(settings.data?.ui_language, ws.data?.ui_language, navigator.language);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // a request that finds its session gone (signed out elsewhere, disabled) sends us back to sign in
  useEffect(() => {
    const onLost = () => qc.invalidateQueries({ queryKey: ["me"] });
    window.addEventListener(UNAUTHORIZED, onLost);
    return () => window.removeEventListener(UNAUTHORIZED, onLost);
  }, [qc]);

  return (
    <I18nProvider lang={lang}>
      <MotionConfig reducedMotion="user">
        {me.isLoading ? (
          <div className="boot" aria-busy="true" />
        ) : signedIn ? (
          <>
            <Live />
            <RouterProvider router={router} />
          </>
        ) : (
          <Login />
        )}
      </MotionConfig>
    </I18nProvider>
  );
}
