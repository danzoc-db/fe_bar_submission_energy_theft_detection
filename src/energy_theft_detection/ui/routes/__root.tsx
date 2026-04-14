import { ThemeProvider } from "@/components/apx/theme-provider";
import { DemoSettingsProvider } from "@/lib/demo-settings";
import { QueryClient } from "@tanstack/react-query";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { Toaster } from "sonner";

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient;
}>()({
  component: () => (
    <ThemeProvider defaultTheme="light" storageKey="apx-ui-theme">
      <DemoSettingsProvider>
        {import.meta.env.DEV && (
          <>
            <TanStackRouterDevtools position="bottom-right" />
          </>
        )}
        <Outlet />
        <Toaster richColors />
      </DemoSettingsProvider>
    </ThemeProvider>
  ),
});
