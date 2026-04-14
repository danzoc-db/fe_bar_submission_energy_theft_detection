import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type ReactNode,
} from "react";
import { Button } from "@/components/ui/button";
import { Download, FileText, Monitor, ScrollText, Presentation } from "lucide-react";

interface SlideDeckProps {
  slides: ReactNode[];
  title?: string;
}

export default function SlideDeck({ slides, title = "Presentation" }: SlideDeckProps) {
  const [mode, setMode] = useState<"scroll" | "slides">("scroll");
  const [currentSlide, setCurrentSlide] = useState(0);
  const [downloading, setDownloading] = useState<"pdf" | "pptx" | null>(null);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const totalSlides = slides.length;

  const goTo = useCallback(
    (idx: number) =>
      setCurrentSlide(Math.max(0, Math.min(idx, totalSlides - 1))),
    [totalSlides],
  );

  useEffect(() => {
    if (mode !== "slides") return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        goTo(currentSlide + 1);
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goTo(currentSlide - 1);
      }
      if (e.key === "Escape") setMode("scroll");
      if (e.key === "f") containerRef.current?.requestFullscreen?.();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mode, currentSlide, goTo]);

  useEffect(() => {
    if (!showDownloadMenu) return;
    const close = () => setShowDownloadMenu(false);
    window.addEventListener("click", close, { once: true });
    return () => window.removeEventListener("click", close);
  }, [showDownloadMenu]);

  async function handleDownloadPdf() {
    setDownloading("pdf");
    setShowDownloadMenu(false);
    try {
      const prevMode = mode;
      setMode("slides");
      await new Promise((r) => setTimeout(r, 200));

      const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
        import("html2canvas-pro"),
        import("jspdf"),
      ]);
      const pdf = new jsPDF({ orientation: "landscape", unit: "px", format: [1280, 720] });

      for (let i = 0; i < slides.length; i++) {
        setCurrentSlide(i);
        await new Promise((r) => setTimeout(r, 500));
        await new Promise((r) => requestAnimationFrame(r));

        const el = contentRef.current;
        if (!el) continue;

        const canvas = await html2canvas(el, {
          scale: 3,
          useCORS: true,
          backgroundColor: "#ffffff",
        });

        const imgData = canvas.toDataURL("image/png");
        if (i > 0) pdf.addPage([1280, 720], "landscape");
        pdf.addImage(imgData, "PNG", 0, 0, 1280, 720);
      }

      const d = new Date().toISOString().slice(0, 10);
      pdf.save(`${title.replace(/\s+/g, "_")}_${d}.pdf`);
      setMode(prevMode);
    } catch (err) {
      console.error("PDF generation failed:", err);
    } finally {
      setDownloading(null);
    }
  }

  async function handleDownloadPptx() {
    setDownloading("pptx");
    setShowDownloadMenu(false);
    try {
      const prevMode = mode;
      setMode("slides");
      await new Promise((r) => setTimeout(r, 200));

      const [{ default: html2canvas }, { default: PptxGenJS }] = await Promise.all([
        import("html2canvas-pro"),
        import("pptxgenjs"),
      ]);
      const pptx = new PptxGenJS();
      pptx.layout = "LAYOUT_WIDE";
      pptx.author = "Databricks AI Dev Kit";
      pptx.title = title;

      for (let i = 0; i < slides.length; i++) {
        setCurrentSlide(i);
        await new Promise((r) => setTimeout(r, 500));
        await new Promise((r) => requestAnimationFrame(r));

        const el = contentRef.current;
        if (!el) continue;

        const canvas = await html2canvas(el, {
          scale: 3,
          useCORS: true,
          backgroundColor: "#ffffff",
        });

        const slide = pptx.addSlide();
        slide.addImage({
          data: canvas.toDataURL("image/png"),
          x: 0, y: 0, w: "100%", h: "100%",
        });
      }

      const d = new Date().toISOString().slice(0, 10);
      await pptx.writeFile({ fileName: `${title.replace(/\s+/g, "_")}_${d}.pptx` });
      setMode(prevMode);
    } catch (err) {
      console.error("PPTX generation failed:", err);
    } finally {
      setDownloading(null);
    }
  }

  const downloadButton = (
    <div className="relative">
      <Button
        size="sm"
        variant="outline"
        onClick={(e) => {
          e.stopPropagation();
          setShowDownloadMenu(!showDownloadMenu);
        }}
        disabled={downloading !== null}
        className="gap-1"
      >
        <Download className="h-4 w-4" />
        {downloading ? "Exporting…" : "Download"}
      </Button>
      {showDownloadMenu && (
        <div className="absolute right-0 top-full mt-1 bg-background border rounded-lg shadow-lg py-1 min-w-[160px] z-[60]">
          <button
            onClick={handleDownloadPdf}
            className="w-full px-3 py-2 text-left text-sm hover:bg-muted flex items-center gap-2"
          >
            <FileText className="h-4 w-4" />
            Download as PDF
          </button>
          <button
            onClick={handleDownloadPptx}
            className="w-full px-3 py-2 text-left text-sm hover:bg-muted flex items-center gap-2"
          >
            <Presentation className="h-4 w-4" />
            Download as PPTX
          </button>
        </div>
      )}
    </div>
  );

  if (mode === "scroll") {
    return (
      <div className="relative">
        <div className="sticky top-0 flex justify-end gap-2 z-10 pb-4">
          {downloadButton}
          <Button
            size="sm"
            variant="outline"
            onClick={() => setMode("slides")}
            className="gap-1"
          >
            <Monitor className="h-4 w-4" />
            Slide View
          </Button>
        </div>
        <div className="space-y-16 pb-16 max-w-5xl mx-auto">
          {slides.map((slide, i) => (
            <div key={i}>
              {slide}
              {i < slides.length - 1 && (
                <hr className="border-t border-border mt-16" />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-50 bg-background flex flex-col"
    >
      <div className="absolute top-4 right-4 z-50 flex gap-2">
        {downloadButton}
        <Button
          size="sm"
          variant="outline"
          onClick={() => setMode("scroll")}
          className="gap-1"
        >
          <ScrollText className="h-4 w-4" />
          Scroll View
        </Button>
      </div>

      <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
        <div ref={contentRef} className="max-w-5xl w-full">
          {slides[currentSlide]}
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 pb-6">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => goTo(currentSlide - 1)}
          disabled={currentSlide === 0}
        >
          &larr; Previous
        </Button>

        <div className="flex gap-1.5">
          {Array.from({ length: totalSlides }).map((_, i) => (
            <button
              key={i}
              onClick={() => goTo(i)}
              className={`h-2 rounded-full transition-all ${
                i === currentSlide
                  ? "w-6 bg-primary"
                  : "w-2 bg-muted-foreground/30"
              }`}
            />
          ))}
        </div>

        <span className="text-xs text-muted-foreground min-w-[4ch] text-center">
          {currentSlide + 1} / {totalSlides}
        </span>

        <Button
          size="sm"
          variant="ghost"
          onClick={() => goTo(currentSlide + 1)}
          disabled={currentSlide === totalSlides - 1}
        >
          Next &rarr;
        </Button>
      </div>

      <p className="text-center text-xs text-muted-foreground pb-2">
        Use &larr; &rarr; arrow keys to navigate &middot; F for fullscreen &middot; Esc to exit
      </p>
    </div>
  );
}
