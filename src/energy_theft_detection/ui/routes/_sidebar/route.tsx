import SidebarLayout from "@/components/apx/sidebar-layout";
import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import { useGetReadiness } from "@/lib/api";
import { useDemoSettings } from "@/lib/demo-settings";
import {
  LayoutDashboard,
  Search,
  ShieldCheck,
  Blocks,
  Home,
  Bot,
  Swords,
} from "lucide-react";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";

export const Route = createFileRoute("/_sidebar")({
  component: () => <Layout />,
});

function Layout() {
  const location = useLocation();
  useGetReadiness({ query: { staleTime: 60_000 } });
  const { competeEnabled } = useDemoSettings();

  const navItems = [
    {
      to: "/dashboard",
      label: "Executive Dashboard",
      icon: <LayoutDashboard size={16} />,
      match: (path: string) => path === "/dashboard",
      group: "👩‍💼 Susie's Dashboard",
    },
    {
      to: "/investigation",
      label: "Investigation Workbench",
      icon: <Search size={16} />,
      match: (path: string) => path.startsWith("/investigation"),
      group: "🕵️ Robbie's Workbench",
    },
    {
      to: "/governance",
      label: "AI Governance",
      icon: <ShieldCheck size={16} />,
      match: (path: string) => path === "/governance",
      group: "Platform",
    },
    {
      to: "/board-report",
      label: "Agent Atlas",
      icon: <Bot size={16} />,
      match: (path: string) => path === "/board-report",
      group: "Platform",
    },
    ...(competeEnabled
      ? [
          {
            to: "/why-databricks" as const,
            label: "Why Databricks",
            icon: <Swords size={16} />,
            match: (path: string) => path === "/why-databricks",
            group: "Platform",
          },
        ]
      : []),
    {
      to: "/presentation",
      label: "Build an App Like This",
      icon: <Blocks size={16} />,
      match: (path: string) => path === "/presentation",
      group: "Platform",
    },
  ];

  const groups = [...new Set(navItems.map((i) => i.group))];

  return (
    <SidebarLayout>
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <Link
                to="/"
                className="flex items-center gap-2 p-2 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Home size={16} />
                <span>Back to Home</span>
              </Link>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
      <SidebarSeparator />
      {groups.map((group) => (
        <SidebarGroup key={group}>
          <SidebarGroupLabel>{group}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems
                .filter((item) => item.group === group)
                .map((item) => (
                  <SidebarMenuItem key={item.to}>
                    <Link
                      to={item.to}
                      className={cn(
                        "flex items-center gap-2 p-2 rounded-lg",
                        item.match(location.pathname)
                          ? "bg-sidebar-accent text-sidebar-accent-foreground"
                          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                      )}
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </Link>
                  </SidebarMenuItem>
                ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      ))}
    </SidebarLayout>
  );
}
