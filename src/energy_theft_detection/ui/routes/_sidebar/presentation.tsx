import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  ArrowRight,
  Blocks,
  ExternalLink,
  GitBranch,
  Layers,
  MessageSquareQuote,
  Sparkles,
  Swords,
  Wrench,
} from "lucide-react";

const SHOW_NOT_TELL_REPO =
  "https://github.com/databricks-field-eng/show-not-tell-apps";

const FEATURES = [
  {
    icon: Sparkles,
    title: "Hero Page with Exec Messaging",
    tag: "PRD-driven impact",
    description:
      "The home page turns PRD pain points into sourced executive metrics — £1.4bn industry theft, £323M UKI Gas exposure, persona cards for Susie and Robbie, and a one-line value proposition. Every figure links back to RECCo, Ofgem, and public filings via tooltips.",
    highlights: [
      "Quantified business problem from docs/PRD.md",
      "Sourced metric cards with Info tooltips",
      "Persona-driven demo walkthrough anchors",
    ],
    cta: { label: "Open hero page", to: "/" as const },
    accent: "border-[#FF8A3D]/40 bg-[#FF8A3D]/5",
    iconColor: "text-[#FF8A3D]",
  },
  {
    icon: Layers,
    title: "Architecture Elements & Diagram",
    tag: "Show the platform story",
    description:
      "A swim-lane architecture diagram on the hero page maps ingestion, ML scoring, Genie, Agent Atlas, and governance into one Databricks platform narrative — replacing a boxy as-is diagram with a clean to-be story customers can follow.",
    highlights: [
      "Interactive ArchitectureDiagram component",
      "Product-coloured lanes (Lakehouse, ML, Genie, Agents)",
      "Scroll anchor from Investigation workbench",
    ],
    cta: { label: "View architecture", to: "/" as const, hash: "architecture" },
    accent: "border-accent/40 bg-accent/5",
    iconColor: "text-accent",
  },
  {
    icon: Wrench,
    title: "Under the Hood Tooltips",
    tag: "Behind the scenes",
    description:
      "Orange wrench panels on Dashboard, Investigation, Governance, and Board Report explain what is really running — Serverless pipelines, Genie spaces, UC Metric Views, MLflow, AI Gateway, and Unity Catalog lineage — without leaving the demo flow.",
    highlights: [
      "Portal panels with compete depth messaging",
      "Triggered from product cards across routes",
      "SA talk-track without switching to slides",
    ],
    cta: { label: "See on Dashboard", to: "/dashboard" as const },
    accent: "border-[#FF3621]/40 bg-[#FF3621]/5",
    iconColor: "text-[#FF3621]",
  },
  {
    icon: Swords,
    title: "Compete Messaging",
    tag: "Why not Fabric?",
    description:
      "When enabled in Demo Settings, Fabric compete tooltips surface on Under the Hood panels and a dedicated Why Databricks advisory page. Claims are sourced from compete/fabric.yaml — editable, versioned, and scoped to products this app actually uses.",
    highlights: [
      "YAML registry (compete/fabric.yaml)",
      "Toggle via Demo Settings on hero page",
      "Contextual depth on Genie, UC, Serverless SQL",
    ],
    cta: { label: "Why Databricks", to: "/why-databricks" as const },
    accent: "border-red-400/40 bg-red-500/5",
    iconColor: "text-red-500",
  },
] as const;

const GETTING_STARTED = [
  {
    step: "1",
    title: "Prerequisites",
    body: "A Databricks App (APX, Streamlit, Dash, Gradio, Flask, FastAPI, or Reflex) plus a PRD or README the skill can read.",
  },
  {
    step: "2",
    title: "Best prompt",
    body: '"Add a presentation page to my app that shows the architecture and value props from my PRD" — or simply "show not tell apps".',
  },
  {
    step: "3",
    title: "What the skill does",
    body: "Auto-detects your framework and UI, extracts pain points and architecture from the PRD, asks about customer branding and compete target (e.g. Fabric), then embeds the pitch inside your app — never a separate PowerPoint.",
  },
  {
    step: "4",
    title: "APX richness",
    body: "This demo uses APX (FastAPI + React) for the richest output: React components, hand-crafted diagrams, compete tooltips, persona cards, and client-side export options.",
  },
] as const;

export const Route = createFileRoute("/_sidebar/presentation")({
  component: BuildAnAppLikeThisPage,
});

function FeatureCard({
  icon: Icon,
  title,
  tag,
  description,
  highlights,
  cta,
  accent,
  iconColor,
}: (typeof FEATURES)[number]) {
  return (
    <Card className={`h-full flex flex-col ${accent}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className={`rounded-lg border bg-background p-2.5 ${iconColor}`}>
            <Icon className="h-5 w-5" />
          </div>
          <Badge variant="outline" className="text-[10px] shrink-0">
            {tag}
          </Badge>
        </div>
        <CardTitle className="text-lg leading-snug pt-2">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4 pt-0">
        <p className="text-sm text-muted-foreground leading-relaxed">{description}</p>
        <ul className="space-y-1.5 text-xs text-muted-foreground">
          {highlights.map((item) => (
            <li key={item} className="flex items-start gap-2">
              <span className="mt-1.5 h-1 w-1 rounded-full bg-foreground/40 shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
        <div className="mt-auto pt-2">
          {"hash" in cta && cta.hash ? (
            <Link
              to={cta.to}
              hash={cta.hash}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
            >
              {cta.label}
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          ) : (
            <Link
              to={cta.to}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
            >
              {cta.label}
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function BuildAnAppLikeThisPage() {
  return (
    <div className="space-y-10 pb-8">
      {/* Header */}
      <section className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="gap-1.5 border-accent/40 text-accent">
            <Blocks className="h-3 w-3" />
            Show Not Tell Apps
          </Badge>
          <Badge variant="secondary" className="text-[10px]">
            APX · FastAPI + React
          </Badge>
        </div>
        <div className="space-y-3 max-w-3xl">
          <h1 className="text-3xl font-bold tracking-tight">Build an App Like This</h1>
          <p className="text-muted-foreground leading-relaxed">
            This demo was shaped with{" "}
            <a
              href={SHOW_NOT_TELL_REPO}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-foreground underline underline-offset-2 hover:text-accent"
            >
              Show Not Tell Apps
            </a>
            — a Field Engineering skill that turns every Databricks App into its own pitch
            deck. The presentation is embedded in the app itself: exec messaging on the hero,
            architecture storytelling, SA talk-track tooltips, and optional compete messaging —
            no PowerPoint required.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <a href={SHOW_NOT_TELL_REPO} target="_blank" rel="noopener noreferrer">
              <GitBranch className="h-4 w-4" />
              View on GitHub
              <ExternalLink className="h-3.5 w-3.5 ml-1 opacity-70" />
            </a>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/">
              Back to demo hero
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      <Separator />

      {/* Feature grid */}
      <section className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Show Not Tell features in this app</h2>
          <p className="text-sm text-muted-foreground">
            Four patterns from the skill — each wired to a live route you can click through
            during a customer demo.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </section>

      <Separator />

      {/* Getting started */}
      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <MessageSquareQuote className="h-5 w-5 text-accent" />
          <h2 className="text-xl font-semibold">Getting started with Show Not Tell</h2>
        </div>
        <p className="text-sm text-muted-foreground max-w-3xl">
          Install the skill via the AI Dev Kit / vibe marketplace, open your Databricks App
          project, and use the prompt below. The skill walks through framework detection,
          PRD extraction, branding, compete target, and tone — then generates an embedded
          presentation route.
        </p>
        <Card className="bg-muted/30 border-dashed">
          <CardContent className="pt-6">
            <p className="text-sm font-mono text-foreground/90 leading-relaxed">
              Add a presentation page to my app that shows the architecture and value props
              from my PRD
            </p>
          </CardContent>
        </Card>
        <div className="grid sm:grid-cols-2 gap-4">
          {GETTING_STARTED.map((item) => (
            <div key={item.step} className="rounded-lg border bg-card p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/10 text-xs font-bold text-accent">
                  {item.step}
                </span>
                <h3 className="font-semibold text-sm">{item.title}</h3>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed pl-8">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <Card className="border-accent/30 bg-accent/5">
        <CardContent className="pt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <p className="font-semibold">Every Databricks App becomes its own pitch deck.</p>
            <p className="text-sm text-muted-foreground">
              Apache 2.0 · contribute via the{" "}
              <a
                href="https://github.com/databricks-field-eng/vibe"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-foreground"
              >
                vibe marketplace
              </a>
            </p>
          </div>
          <Button variant="outline" asChild className="shrink-0">
            <a href={SHOW_NOT_TELL_REPO} target="_blank" rel="noopener noreferrer">
              databricks-field-eng/show-not-tell-apps
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
