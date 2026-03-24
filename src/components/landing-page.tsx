'use client';

import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  forwardRef,
  useImperativeHandle,
  useMemo,
  type FormEvent,
} from "react";
import {
  motion,
  AnimatePresence,
  useScroll,
  useMotionValueEvent,
  type Transition,
  type VariantLabels,
  type Target,
  type LegacyAnimationControls,
  type TargetAndTransition,
  type Variants,
} from "framer-motion";
import {
  Database,
  Shield,
  Network,
  Brain,
  Zap,
  Lock,
  Users,
  Activity,
  ChevronRight,
  Menu,
  X,
  Mail,
  MapPin,
  Github,
  Linkedin,
  Twitter,
  Wifi,
  CreditCard,
  Video,
  Eye,
  Megaphone,
  ThumbsUp,
  ArrowRight,
  Scale,
} from "lucide-react";
import { useLanyard } from "react-use-phplanyard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface RotatingTextRef {
  next: () => void;
  previous: () => void;
  jumpTo: (index: number) => void;
  reset: () => void;
}

interface RotatingTextProps
  extends Omit<
    React.ComponentPropsWithoutRef<typeof motion.span>,
    "children" | "transition" | "initial" | "animate" | "exit"
  > {
  texts: string[];
  transition?: Transition;
  initial?: boolean | Target | VariantLabels;
  animate?: boolean | VariantLabels | LegacyAnimationControls | TargetAndTransition;
  exit?: Target | VariantLabels;
  animatePresenceMode?: "sync" | "wait";
  animatePresenceInitial?: boolean;
  rotationInterval?: number;
  staggerDuration?: number;
  staggerFrom?: "first" | "last" | "center" | "random" | number;
  loop?: boolean;
  auto?: boolean;
  splitBy?: "characters" | "words" | "lines" | string;
  onNext?: (index: number) => void;
  mainClassName?: string;
  splitLevelClassName?: string;
  elementLevelClassName?: string;
}

const RotatingText = forwardRef<RotatingTextRef, RotatingTextProps>(
  (
    {
      texts,
      transition = { type: "spring", damping: 25, stiffness: 300 },
      initial = { y: "100%", opacity: 0 },
      animate = { y: 0, opacity: 1 },
      exit = { y: "-120%", opacity: 0 },
      animatePresenceMode = "wait",
      animatePresenceInitial = false,
      rotationInterval = 2200,
      staggerDuration = 0.01,
      staggerFrom = "last",
      loop = true,
      auto = true,
      splitBy = "characters",
      onNext,
      mainClassName,
      splitLevelClassName,
      elementLevelClassName,
      ...rest
    },
    ref
  ) => {
    const [currentTextIndex, setCurrentTextIndex] = useState<number>(0);

    const splitIntoCharacters = (text: string): string[] => {
      if (typeof Intl !== "undefined" && Intl.Segmenter) {
        try {
          const segmenter = new Intl.Segmenter("en", {
            granularity: "grapheme",
          });
          return Array.from(
            segmenter.segment(text),
            (segment) => segment.segment
          );
        } catch (error) {
          console.error("Error using Intl.Segmenter:", error);
          return text.split("");
        }
      }
      return text.split("");
    };

    const elements = useMemo(() => {
      const currentText: string = texts[currentTextIndex] ?? "";
      if (splitBy === "characters") {
        const words = currentText.split(/(\s+)/);
        let charCount = 0;
        return words
          .filter((part) => part.length > 0)
          .map((part) => {
            const isSpace = /^\s+$/.test(part);
            const chars = isSpace ? [part] : splitIntoCharacters(part);
            const startIndex = charCount;
            charCount += chars.length;
            return {
              characters: chars,
              isSpace: isSpace,
              startIndex: startIndex,
            };
          });
      }
      if (splitBy === "words") {
        return currentText
          .split(/(\s+)/)
          .filter((word) => word.length > 0)
          .map((word, i) => ({
            characters: [word],
            isSpace: /^\s+$/.test(word),
            startIndex: i,
          }));
      }
      if (splitBy === "lines") {
        return currentText.split("\n").map((line, i) => ({
          characters: [line],
          isSpace: false,
          startIndex: i,
        }));
      }
      return currentText.split(splitBy).map((part, i) => ({
        characters: [part],
        isSpace: false,
        startIndex: i,
      }));
    }, [texts, currentTextIndex, splitBy]);

    const totalElements = useMemo(
      () => elements.reduce((sum, el) => sum + el.characters.length, 0),
      [elements]
    );

    const getStaggerDelay = useCallback(
      (index: number, total: number): number => {
        if (total <= 1 || !staggerDuration) return 0;
        const stagger = staggerDuration;
        switch (staggerFrom) {
          case "first":
            return index * stagger;
          case "last":
            return (total - 1 - index) * stagger;
          case "center":
            const center = (total - 1) / 2;
            return Math.abs(center - index) * stagger;
          case "random":
            return Math.random() * (total - 1) * stagger;
          default:
            if (typeof staggerFrom === "number") {
              const fromIndex = Math.max(0, Math.min(staggerFrom, total - 1));
              return Math.abs(fromIndex - index) * stagger;
            }
            return index * stagger;
        }
      },
      [staggerFrom, staggerDuration]
    );

    const handleIndexChange = useCallback(
      (newIndex: number) => {
        setCurrentTextIndex(newIndex);
        onNext?.(newIndex);
      },
      [onNext]
    );

    const next = useCallback(() => {
      const nextIndex =
        currentTextIndex === texts.length - 1
          ? loop
            ? 0
            : currentTextIndex
          : currentTextIndex + 1;
      if (nextIndex !== currentTextIndex) handleIndexChange(nextIndex);
    }, [currentTextIndex, texts.length, loop, handleIndexChange]);

    const previous = useCallback(() => {
      const prevIndex =
        currentTextIndex === 0
          ? loop
            ? texts.length - 1
            : currentTextIndex
          : currentTextIndex - 1;
      if (prevIndex !== currentTextIndex) handleIndexChange(prevIndex);
    }, [currentTextIndex, texts.length, loop, handleIndexChange]);

    const jumpTo = useCallback(
      (index: number) => {
        const validIndex = Math.max(0, Math.min(index, texts.length - 1));
        if (validIndex !== currentTextIndex) handleIndexChange(validIndex);
      },
      [texts.length, currentTextIndex, handleIndexChange]
    );

    const reset = useCallback(() => {
      if (currentTextIndex !== 0) handleIndexChange(0);
    }, [currentTextIndex, handleIndexChange]);

    useImperativeHandle(ref, () => ({ next, previous, jumpTo, reset }), [
      next,
      previous,
      jumpTo,
      reset,
    ]);

    useEffect(() => {
      if (!auto || texts.length <= 1) return;
      const intervalId = setInterval(next, rotationInterval);
      return () => clearInterval(intervalId);
    }, [next, rotationInterval, auto, texts.length]);

    return (
      <motion.span
        className={cn(
          "inline-flex flex-wrap whitespace-pre-wrap relative align-bottom pb-[10px]",
          mainClassName
        )}
        {...rest}
        layout
      >
        <span className="sr-only">{texts[currentTextIndex]}</span>
        <AnimatePresence
          mode={animatePresenceMode}
          initial={animatePresenceInitial}
        >
          <motion.div
            key={currentTextIndex}
            className={cn(
              "inline-flex flex-wrap relative",
              splitBy === "lines"
                ? "flex-col items-start w-full"
                : "flex-row items-baseline"
            )}
            layout
            aria-hidden="true"
            initial="initial"
            animate="animate"
            exit="exit"
          >
            {elements.map((elementObj, elementIndex) => (
              <span
                key={elementIndex}
                className={cn(
                  "inline-flex",
                  splitBy === "lines" ? "w-full" : "",
                  splitLevelClassName
                )}
                style={{ whiteSpace: "pre" }}
              >
                {elementObj.characters.map((char, charIndex) => {
                  const globalIndex = elementObj.startIndex + charIndex;
                  return (
                    <motion.span
                      key={`${char}-${charIndex}`}
                      initial={initial}
                      animate={animate}
                      exit={exit}
                      transition={{
                        ...transition,
                        delay: getStaggerDelay(globalIndex, totalElements),
                      }}
                      className={cn(
                        "inline-block leading-none tracking-tight",
                        elementLevelClassName
                      )}
                    >
                      {char === " " ? "\u00A0" : char}
                    </motion.span>
                  );
                })}
              </span>
            ))}
          </motion.div>
        </AnimatePresence>
      </motion.span>
    );
  }
);
RotatingText.displayName = "RotatingText";

const itemFadeIn: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

interface Dot {
  x: number;
  y: number;
  targetOpacity: number;
  currentOpacity: number;
  opacitySpeed: number;
  baseRadius: number;
  currentRadius: number;
}

interface TeamMember {
  name: string;
  initials: string;
  imageUrl?: string;
  discordId?: string;
  role: string;
  description: string;
  icon: React.ReactNode;
  specialty: string;
  tech: string;
  isAccent: boolean;
}

const statusColors: Record<string, string> = {
  online: "bg-emerald-500",
  idle: "bg-amber-400",
  dnd: "bg-rose-400",
  offline: "bg-gray-400",
};

const statusMapping: Record<string, string> = {
  online: "Online",
  idle: "Idle",
  dnd: "DND",
};

const DiscordStatusIndicator: React.FC<{ discordId: string }> = ({ discordId }) => {
  const { loading, status } = useLanyard({
    userId: discordId,
    socket: true,
  });

  if (loading || !status) {
    return null;
  }

  const discordStatus = status.discord_status || "offline";
  const isMobile = status.active_on_discord_mobile;
  const isDesktop = status.active_on_discord_desktop || status.active_on_discord_web;

  const validStatus = statusMapping[discordStatus] || "Offline";
  const statusText = isMobile
    ? `${validStatus} on Phone`
    : isDesktop
      ? `${validStatus} on Desktop`
      : "Zzz...";

  return (
    <div className="absolute bottom-1 right-1 w-4 h-4 rounded-full ring-[3px] ring-[var(--color-bg-surface)] group/status flex justify-center">
      <span
        className={cn("w-full h-full rounded-full", statusColors[discordStatus])}
        role="status"
        aria-label={statusText}
      >
        <span className="sr-only">{statusText}</span>
      </span>

      {/* Hover Tooltip */}
      <div
        className="absolute z-10 mb-1 px-2 py-1 bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-xs opacity-0 group-hover/status:opacity-100 transition-opacity pointer-events-none bottom-full rounded-md whitespace-nowrap"
        aria-hidden="true"
      >
        {statusText}
      </div>
    </div>
  );
};

const TeamMemberCard: React.FC<{ member: TeamMember }> = ({ member }) => {
  const [imageError, setImageError] = useState(false);

  return (
    <motion.div
      variants={itemFadeIn}
      className={cn(
        "group relative overflow-hidden rounded-xl p-8 flex flex-col justify-between min-h-[400px]",
        member.isAccent ? "card-accent" : "card-surface"
      )}
    >
      <div className="space-y-4">
        <div className="flex items-start gap-4">
          <div
            className={cn(
              "flex-shrink-0 w-20 h-20 rounded-full flex items-center justify-center font-bold text-xl transition-transform group-hover:scale-105 relative",
              member.isAccent
                ? "bg-[var(--color-accent)] text-[var(--color-bg-primary)]"
                : "bg-[var(--color-bg-elevated)] border-2 border-[var(--color-border-default)] text-[var(--color-text-primary)]"
            )}
          >
            {member.imageUrl && !imageError ? (
              <img
                src={member.imageUrl}
                alt={member.name}
                className="w-full h-full object-cover rounded-full"
                onError={() => setImageError(true)}
              />
            ) : (
              member.initials
            )}
            {member.discordId && <DiscordStatusIndicator discordId={member.discordId} />}
          </div>
          <div className="flex-1">
            <h3 className="text-2xl font-bold mb-2 text-[var(--color-text-primary)]">
              {member.name}
            </h3>
            <p className="text-sm font-medium text-[var(--color-accent)] uppercase tracking-wider">
              {member.role}
            </p>
          </div>
        </div>
        <p className="text-[var(--color-text-secondary)] leading-relaxed">
          {member.description}
        </p>
      </div>

      <div className="mt-8 pt-6 border-t border-[var(--color-border-default)]">
        <div className="flex items-center gap-2 mb-2">
          {member.icon}
          <span className="text-sm font-medium text-[var(--color-accent)] uppercase tracking-wide">
            {member.specialty}
          </span>
        </div>
        <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">
          {member.tech}
        </p>
      </div>
    </motion.div>
  );
};

// Helper to parse CSS color values into RGB
function parseCssColor(color: string): { r: number; g: number; b: number } | null {
  const trimmed = color.trim();

  // Handle hex format (#RGB or #RRGGBB)
  if (trimmed.startsWith('#')) {
    const hex = trimmed.substring(1);
    if (hex.length === 3) {
      // 3-digit hex (#RGB)
      return {
        r: parseInt(hex[0] + hex[0], 16),
        g: parseInt(hex[1] + hex[1], 16),
        b: parseInt(hex[2] + hex[2], 16),
      };
    } else if (hex.length === 6) {
      // 6-digit hex (#RRGGBB)
      return {
        r: parseInt(hex.substring(0, 2), 16),
        g: parseInt(hex.substring(2, 4), 16),
        b: parseInt(hex.substring(4, 6), 16),
      };
    }
  }

  // Handle rgb() or rgba() format — comma-separated or modern space-separated
  const rgbMatch = trimmed.match(/rgba?\s*\(\s*(\d+)(?:\s*,\s*|\s+)(\d+)(?:\s*,\s*|\s+)(\d+)(?:[^)]*)?/i);
  if (rgbMatch) {
    return {
      r: parseInt(rgbMatch[1], 10),
      g: parseInt(rgbMatch[2], 10),
      b: parseInt(rgbMatch[3], 10),
    };
  }

  return null;
}

const FazriAnalyzerLanding: React.FC = () => {
    const { data: session } = useSession();
    const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameId = useRef<number | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isScrolled, setIsScrolled] = useState<boolean>(false);
  const accentColorRGB = useRef<{r: number, g: number, b: number}>({ r: 200, g: 241, b: 53 });

  const { scrollY } = useScroll();
  useMotionValueEvent(scrollY, "change", (latest) => {
    setIsScrolled(latest > 10);
  });

  // Compute accent color from CSS variable and update on theme change
  useEffect(() => {
    const readAccentColor = () => {
      const accentColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--color-accent')
        .trim();
      const parsed = parseCssColor(accentColor);
      if (parsed) {
        accentColorRGB.current = parsed;
      }
    };

    readAccentColor();

    const observer = new MutationObserver(readAccentColor);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class', 'style', 'data-theme'],
    });

    return () => observer.disconnect();
  }, []);

  const dotsRef = useRef<Dot[]>([]);
  const gridRef = useRef<Record<string, number[]>>({});
  const canvasSizeRef = useRef<{ width: number; height: number }>({
    width: 0,
    height: 0,
  });
  const mousePositionRef = useRef<{ x: number | null; y: number | null }>({
    x: null,
    y: null,
  });

  const DOT_SPACING = 25;
  const BASE_OPACITY_MIN = 0.4;
  const BASE_OPACITY_MAX = 0.5;
  const BASE_RADIUS = 1;
  const INTERACTION_RADIUS = 150;
  const INTERACTION_RADIUS_SQ = INTERACTION_RADIUS * INTERACTION_RADIUS;
  const OPACITY_BOOST = 0.6;
  const RADIUS_BOOST = 2.5;
  const GRID_CELL_SIZE = Math.max(50, Math.floor(INTERACTION_RADIUS / 1.5));

  const handleMouseMove = useCallback((event: globalThis.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      mousePositionRef.current = { x: null, y: null };
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const canvasX = event.clientX - rect.left;
    const canvasY = event.clientY - rect.top;
    mousePositionRef.current = { x: canvasX, y: canvasY };
  }, []);

  const createDots = useCallback(() => {
    const { width, height } = canvasSizeRef.current;
    if (width === 0 || height === 0) return;

    const newDots: Dot[] = [];
    const newGrid: Record<string, number[]> = {};
    const cols = Math.ceil(width / DOT_SPACING);
    const rows = Math.ceil(height / DOT_SPACING);

    for (let i = 0; i < cols; i++) {
      for (let j = 0; j < rows; j++) {
        const x = i * DOT_SPACING + DOT_SPACING / 2;
        const y = j * DOT_SPACING + DOT_SPACING / 2;
        const cellX = Math.floor(x / GRID_CELL_SIZE);
        const cellY = Math.floor(y / GRID_CELL_SIZE);
        const cellKey = `${cellX}_${cellY}`;

        if (!newGrid[cellKey]) {
          newGrid[cellKey] = [];
        }

        const dotIndex = newDots.length;
        newGrid[cellKey].push(dotIndex);

        const baseOpacity =
          Math.random() * (BASE_OPACITY_MAX - BASE_OPACITY_MIN) +
          BASE_OPACITY_MIN;
        newDots.push({
          x,
          y,
          targetOpacity: baseOpacity,
          currentOpacity: baseOpacity,
          opacitySpeed: Math.random() * 0.005 + 0.002,
          baseRadius: BASE_RADIUS,
          currentRadius: BASE_RADIUS,
        });
      }
    }
    dotsRef.current = newDots;
    gridRef.current = newGrid;
  }, [
    DOT_SPACING,
    GRID_CELL_SIZE,
    BASE_OPACITY_MIN,
    BASE_OPACITY_MAX,
    BASE_RADIUS,
  ]);

  const handleResize = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const container = canvas.parentElement;
    const width = container ? container.clientWidth : window.innerWidth;
    const height = container ? container.clientHeight : window.innerHeight;

    if (
      canvas.width !== width ||
      canvas.height !== height ||
      canvasSizeRef.current.width !== width ||
      canvasSizeRef.current.height !== height
    ) {
      canvas.width = width;
      canvas.height = height;
      canvasSizeRef.current = { width, height };
      createDots();
    }
  }, [createDots]);

  const animateDots = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const dots = dotsRef.current;
    const grid = gridRef.current;
    const { width, height } = canvasSizeRef.current;
    const { x: mouseX, y: mouseY } = mousePositionRef.current;

    if (!ctx || !dots || !grid || width === 0 || height === 0) {
      animationFrameId.current = requestAnimationFrame(animateDots);
      return;
    }

    ctx.clearRect(0, 0, width, height);

    const activeDotIndices = new Set<number>();
    if (mouseX !== null && mouseY !== null) {
      const mouseCellX = Math.floor(mouseX / GRID_CELL_SIZE);
      const mouseCellY = Math.floor(mouseY / GRID_CELL_SIZE);
      const searchRadius = Math.ceil(INTERACTION_RADIUS / GRID_CELL_SIZE);
      for (let i = -searchRadius; i <= searchRadius; i++) {
        for (let j = -searchRadius; j <= searchRadius; j++) {
          const checkCellX = mouseCellX + i;
          const checkCellY = mouseCellY + j;
          const cellKey = `${checkCellX}_${checkCellY}`;
          if (grid[cellKey]) {
            grid[cellKey].forEach((dotIndex) => activeDotIndices.add(dotIndex));
          }
        }
      }
    }

    dots.forEach((dot, index) => {
      dot.currentOpacity += dot.opacitySpeed;
      if (
        dot.currentOpacity >= dot.targetOpacity ||
        dot.currentOpacity <= BASE_OPACITY_MIN
      ) {
        dot.opacitySpeed = -dot.opacitySpeed;
        dot.currentOpacity = Math.max(
          BASE_OPACITY_MIN,
          Math.min(dot.currentOpacity, BASE_OPACITY_MAX)
        );
        dot.targetOpacity =
          Math.random() * (BASE_OPACITY_MAX - BASE_OPACITY_MIN) +
          BASE_OPACITY_MIN;
      }

      let interactionFactor = 0;
      dot.currentRadius = dot.baseRadius;

      if (mouseX !== null && mouseY !== null && activeDotIndices.has(index)) {
        const dx = dot.x - mouseX;
        const dy = dot.y - mouseY;
        const distSq = dx * dx + dy * dy;

        if (distSq < INTERACTION_RADIUS_SQ) {
          const distance = Math.sqrt(distSq);
          interactionFactor = Math.max(0, 1 - distance / INTERACTION_RADIUS);
          interactionFactor = interactionFactor * interactionFactor;
        }
      }

      const finalOpacity = Math.min(
        1,
        dot.currentOpacity + interactionFactor * OPACITY_BOOST
      );
      dot.currentRadius = dot.baseRadius + interactionFactor * RADIUS_BOOST;

      const { r, g, b } = accentColorRGB.current;
      ctx.beginPath();
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${finalOpacity.toFixed(3)})`;
      ctx.arc(dot.x, dot.y, dot.currentRadius, 0, Math.PI * 2);
      ctx.fill();
    });

    animationFrameId.current = requestAnimationFrame(animateDots);
  }, [
    GRID_CELL_SIZE,
    INTERACTION_RADIUS,
    INTERACTION_RADIUS_SQ,
    OPACITY_BOOST,
    RADIUS_BOOST,
    BASE_OPACITY_MIN,
    BASE_OPACITY_MAX,
  ]);

  useEffect(() => {
    handleResize();
    const handleMouseLeave = () => {
      mousePositionRef.current = { x: null, y: null };
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("resize", handleResize);
    document.documentElement.addEventListener("mouseleave", handleMouseLeave);

    animationFrameId.current = requestAnimationFrame(animateDots);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.documentElement.removeEventListener(
        "mouseleave",
        handleMouseLeave
      );
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current);
      }
    };
  }, [handleResize, handleMouseMove, animateDots]);

  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isMobileMenuOpen]);

  const headerVariants: Variants = {
    top: {
      position: "fixed",
    },
    scrolled: {
      position: "fixed",
    },
  };

  const mobileMenuVariants: Variants = {
    hidden: { opacity: 0, y: -20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.2, ease: "easeOut" },
    },
    exit: {
      opacity: 0,
      y: -20,
      transition: { duration: 0.15, ease: "easeIn" },
    },
  };

  const contentDelay = 0.3;
  const itemDelayIncrement = 0.1;

  const bannerVariants: Variants = {
    hidden: { opacity: 0, y: -10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, delay: contentDelay },
    },
  };
  const headlineVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 0.5, delay: contentDelay + itemDelayIncrement },
    },
  };
  const subHeadlineVariants: Variants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        delay: contentDelay + itemDelayIncrement * 2,
      },
    },
  };
  const formVariants: Variants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        delay: contentDelay + itemDelayIncrement * 3,
      },
    },
  };

  const fadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6 },
    },
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const sectionItemFadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 },
    },
  };

  return (
    <div className="pt-[100px] relative min-h-screen flex flex-col bg-[var(--color-bg-primary)] text-[var(--color-text-primary)]">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-0 pointer-events-none opacity-80"
      />

      <motion.header
        variants={headerVariants}
        initial="top"
        animate={isScrolled ? "scrolled" : "top"}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className={cn(
          "px-6 w-full md:px-10 lg:px-16 sticky top-0 z-30 backdrop-blur-md border-b",
          isScrolled ? "header-scrolled" : "header-top"
        )}
      >
        <nav className="flex justify-between items-center max-w-screen-xl mx-auto h-[70px]">
          <div className="flex items-center flex-shrink-0">
            <Database className="h-6 w-6 text-[var(--color-accent)]" />
            <span className="text-xl font-bold ml-2 text-[var(--color-text-primary)]">
              Fazri Analyzer
            </span>
          </div>

          <div className="hidden md:flex items-center justify-center flex-grow space-x-6 lg:space-x-8 px-4">
            <a
              href="#features"
              className="nav-link text-sm font-medium"
            >
              Features
            </a>
            <a
              href="#architecture"
              className="nav-link text-sm font-medium"
            >
              Architecture
            </a>
            <a
              href="#team"
              className="nav-link text-sm font-medium"
            >
              Team
            </a>
            <a
              href="#contact"
              className="nav-link text-sm font-medium"
            >
              Contact
            </a>
          </div>

          <div className="flex items-center flex-shrink-0 space-x-4 lg:space-x-6">
            <Button className="btn-primary" size="lg" onClick={() => router.push('/dashboard')}>
              {session ? "Dashboard" : "Sign in"}
            </Button>

            <motion.button
              className="md:hidden z-50 text-[var(--color-text-secondary)]"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Toggle menu"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              {isMobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </motion.button>
          </div>
        </nav>

        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              key="mobile-menu"
              variants={mobileMenuVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="md:hidden absolute top-full left-0 right-0 backdrop-blur-sm py-4 mobile-menu-bg"
            >
              <div className="flex flex-col items-center space-y-4 px-6">
                <a
                  href="#features"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="nav-link text-sm font-medium"
                >
                  Features
                </a>
                <a
                  href="#architecture"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="nav-link text-sm font-medium"
                >
                  Architecture
                </a>
                <a
                  href="#team"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="nav-link text-sm font-medium"
                >
                  Team
                </a>
                <a
                  href="#contact"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="nav-link text-sm font-medium"
                >
                  Contact
                </a>
                <hr className="w-full border-[var(--color-border-default)]" />
                <a
                  href="/auth"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="nav-link text-sm font-medium"
                >
                  Sign in
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      <main className="flex-grow flex flex-col items-center justify-center text-center px-4 pt-8 pb-16 relative z-10">
        <motion.div
          variants={bannerVariants}
          initial="hidden"
          animate="visible"
          className="mb-6"
        >
          <span
            className="px-4 py-1 rounded-full text-xs sm:text-sm font-medium cursor-pointer transition-colors inline-flex items-center gap-2 badge-accent"
          >
            <Shield className="h-3 w-3" />
            Advanced Entity Resolution & Security Monitoring
          </span>
        </motion.div>

        <motion.h1
          variants={headlineVariants}
          initial="hidden"
          animate="visible"
          className="hero-headline mb-4 mx-auto"
        >
          Campus Security Through
          <br />{" "}
          <span className="inline-block h-[1.2em] sm:h-[1.2em] lg:h-[1.2em] overflow-hidden align-bottom">
            <RotatingText
              texts={[
                "AI Analytics",
                "Graph Intelligence",
                "Entity Resolution",
                "Predictive Monitoring",
                "Real-time Insights",
              ]}
              mainClassName="mx-1 text-[var(--color-accent)]"
              staggerFrom={"last"}
              initial={{ y: "-100%", opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: "110%", opacity: 0 }}
              staggerDuration={0.01}
              transition={{ type: "spring", damping: 18, stiffness: 250 }}
              rotationInterval={2200}
              splitBy="characters"
              auto={true}
              loop={true}
            />
          </span>
        </motion.h1>

        <motion.p
          variants={subHeadlineVariants}
          initial="hidden"
          animate="visible"
          className="text-base sm:text-lg lg:text-xl max-w-2xl mx-auto mb-8 text-[var(--color-text-secondary)]"
        >
          A modular, service-oriented system combining Next.js frontend, FastAPI
          backend, and Neo4j graph analytics for comprehensive campus entity
          resolution and security monitoring.
        </motion.p>

        <motion.form
          variants={formVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col sm:flex-row items-center justify-center gap-2 w-full max-w-md mx-auto mb-3"
          onSubmit={(e: FormEvent<HTMLFormElement>) => e.preventDefault()}
        >
          <Input
            type="email"
            placeholder="Your institutional email"
            required
            aria-label="Institutional Email"
            className="input-field flex-grow w-full sm:w-auto px-4 py-2 rounded-md focus:outline-none focus:ring-2 transition-all"
          />
          <motion.button
            type="submit"
            className="btn-primary w-full sm:w-auto flex-shrink-0"
            whileHover={{ scale: 1.03, y: -1 }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 400, damping: 15 }}
          >
            Request Demo
          </motion.button>
        </motion.form>
      </main>

      <section
        id="features"
        className="section-gap w-full relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto"
        >
          <div className="flex flex-col items-center justify-center space-y-4 text-center mb-12">
            <span className="section-label">Platform Capabilities</span>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl text-[var(--color-text-primary)]"
            >
              Core Features
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mx-auto max-w-[900px] md:text-xl text-[var(--color-text-secondary)]"
            >
              Comprehensive entity resolution and security monitoring powered by
              advanced AI and graph analytics
            </motion.p>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="mx-auto grid max-w-5xl items-center gap-6 md:grid-cols-2 lg:grid-cols-3"
          >
            {[
              {
                icon: <Database className="h-10 w-10 text-[var(--color-accent)]" />,
                title: "Entity Resolution",
                description:
                  "Multi-modal fusion with confidence scoring for accurate entity identification and linking across campus systems.",
              },
              {
                icon: <Network className="h-10 w-10 text-[var(--color-accent)]" />,
                title: "Graph Analytics",
                description:
                  "Neo4j-powered relationship mapping for entity linking, gap detection, and pattern recognition.",
              },
              {
                icon: <Brain className="h-10 w-10 text-[var(--color-accent)]" />,
                title: "Predictive AI",
                description:
                  "ML-powered anomaly detection and behavioral pattern analysis with a configurable rule engine for explainable results.",
              },
              {
                icon: <Shield className="h-10 w-10 text-[var(--color-accent)]" />,
                title: "Security Monitoring",
                description:
                  "Real-time anomaly detection and behavioral monitoring using a configurable rule engine and pattern analysis.",
              },
              {
                icon: <Activity className="h-10 w-10 text-[var(--color-accent)]" />,
                title: "Timeline Generation",
                description:
                  "Graph-based timeline visualization for tracking entity movements and interactions over time.",
              },
              {
                icon: <Lock className="h-10 w-10 text-[var(--color-accent)]" />,
                title: "OAuth & JWT Auth",
                description:
                  "Secure authentication and authorization with Prisma ORM for user data management.",
              },
            ].map((feature, index) => (
              <motion.div
                key={index}
                variants={sectionItemFadeIn}
                whileHover={{ y: -10, transition: { duration: 0.3 } }}
                className="card-surface feature-card group relative overflow-hidden rounded-xl transition-all"
              >
                <div className="space-y-3">
                  <div className="mb-4">{feature.icon}</div>
                  <h3 className="text-xl font-bold text-[var(--color-text-primary)]">
                    {feature.title}
                  </h3>
                  <p className="text-[var(--color-text-secondary)]">{feature.description}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <section
        id="architecture"
        className="section-gap w-full relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto max-w-7xl"
        >
          <div className="mb-12">
            <span className="section-label">THE SOLUTION</span>
            <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold mt-4 text-[var(--color-text-primary)]">
              One data layer.
              <br />
              Five welfare outcomes.
            </h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left Column - Data Sources */}
            <div className="lg:col-span-3 space-y-4">
              <div className="card-surface p-6 rounded-lg">
                <div className="flex items-start gap-3">
                  <Wifi className="h-5 w-5 text-[var(--color-accent)] flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-[var(--color-text-primary)] mb-1">WiFi Logs</h3>
                    <p className="text-sm text-[var(--color-text-secondary)]">Association events</p>
                  </div>
                </div>
              </div>

              <div className="card-surface p-6 rounded-lg">
                <div className="flex items-start gap-3">
                  <CreditCard className="h-5 w-5 text-[var(--color-accent)] flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-[var(--color-text-primary)] mb-1">RFID / Access</h3>
                    <p className="text-sm text-[var(--color-text-secondary)]">Entry/exit records</p>
                  </div>
                </div>
              </div>

              <div className="card-surface p-6 rounded-lg">
                <div className="flex items-start gap-3">
                  <Video className="h-5 w-5 text-[var(--color-accent)] flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="font-semibold text-[var(--color-text-primary)] mb-1">CCTV</h3>
                    <p className="text-sm text-[var(--color-text-secondary)]">Facial recognition events</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Arrow 1 */}
            <div className="hidden lg:flex lg:col-span-1 justify-center">
              <ArrowRight className="h-8 w-8 text-[var(--color-accent)]" />
            </div>

            {/* Center Column - Intelligence Layer */}
            <div className="lg:col-span-4">
              <div className="card-accent p-8 rounded-lg text-center">
                <div className="flex justify-center mb-4">
                  <Brain className="h-16 w-16 text-[var(--color-accent)]" />
                </div>
                <h3 className="text-2xl font-bold mb-6 text-[var(--color-text-primary)]">
                  Fazri Intelligence Layer
                </h3>
                <div className="space-y-2 text-left">
                  <p className="text-[var(--color-text-secondary)]">Entity resolution →</p>
                  <p className="text-[var(--color-text-secondary)]">Behavioral fingerprint →</p>
                  <p className="text-[var(--color-text-secondary)]">Anomaly scoring</p>
                </div>
              </div>
            </div>

            {/* Arrow 2 */}
            <div className="hidden lg:flex lg:col-span-1 justify-center">
              <ArrowRight className="h-8 w-8 text-[var(--color-accent)]" />
            </div>

            {/* Right Column - Welfare Outcomes */}
            <div className="lg:col-span-3 space-y-3">
              <div className="card-surface p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-[var(--color-text-primary)]">Mann Mitra</h4>
                    <p className="text-xs text-[var(--color-text-muted)]">Mental health signals</p>
                  </div>
                  <Brain className="h-5 w-5 text-[var(--color-text-muted)]" />
                </div>
              </div>

              <div className="card-surface p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-[var(--color-text-primary)]">Raksha Chakra</h4>
                    <p className="text-xs text-[var(--color-text-muted)]">Ragging detection</p>
                  </div>
                  <Shield className="h-5 w-5 text-[var(--color-text-muted)]" />
                </div>
              </div>

              <div className="card-surface p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-[var(--color-text-primary)]">Samata Shield</h4>
                    <p className="text-xs text-[var(--color-text-muted)]">Caste discrimination</p>
                  </div>
                  <Scale className="h-5 w-5 text-[var(--color-text-muted)]" />
                </div>
              </div>

              <div className="card-surface p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-[var(--color-text-primary)]">Pratiraksha</h4>
                    <p className="text-xs text-[var(--color-text-muted)]">POSH intelligence</p>
                  </div>
                  <Eye className="h-5 w-5 text-[var(--color-text-muted)]" />
                </div>
              </div>

              <div className="card-surface p-4 rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-[var(--color-text-primary)]">Sanvaad Setu</h4>
                    <p className="text-xs text-[var(--color-text-muted)]">Protest early warning</p>
                  </div>
                  <Megaphone className="h-5 w-5 text-[var(--color-text-muted)]" />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Callout */}
          <div className="mt-12">
            <div className="card-surface p-6 rounded-lg">
              <div className="flex items-center gap-3">
                <ThumbsUp className="h-6 w-6 text-[var(--color-accent)] flex-shrink-0" />
                <div>
                  <span className="font-semibold text-[var(--color-text-primary)]">Hardware-agnostic.</span>
                  <span className="text-[var(--color-text-secondary)]"> Works with infrastructure campuses already own. No new procurement required.</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      <section
        id="team"
        className="section-gap w-full relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto"
        >
          <div className="mb-12">
            <span className="section-label">THE TEAM</span>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="mx-auto grid max-w-6xl gap-6 md:grid-cols-2 lg:grid-cols-3"
          >
            {[
              {
                name: "Sakib Alam",
                initials: "SA",
                imageUrl: undefined, // Use initials as fallback, show image when available
                discordId: "644911200391659539",
                role: "FOUNDER & CEO",
                description: "Architect of the behavioral intelligence layer. Built the entity resolution and anomaly detection core.",
                icon: <Brain className="h-5 w-5 text-[var(--color-accent)]" />,
                specialty: "Baat karne wala",
                tech: "MERN · Pytorch · FastAPI · Communication",
                isAccent: true,
              },
              {
                name: "Subhadeep Pramanik",
                initials: "SP",
                imageUrl: "https://res.cloudinary.com/ddvheihbd/image/upload/f_auto,q_auto/v1/team/phpxcoder",
                discordId: "697757845063729194",
                role: "CO-FOUNDER & CTO",
                description: "Owns production infrastructure, system reliability, and real-time data pipeline architecture.",
                icon: <Database className="h-5 w-5 text-[var(--color-text-secondary)]" />,
                specialty: "deploy karne wala",
                tech: "AWS · Docker · Kubernetes · Jenkins",
                isAccent: false,
              },
              {
                name: "Dinesh Yerra",
                initials: "DY",
                imageUrl: "https://res.cloudinary.com/ddvheihbd/image/upload/t_dino_1_1/team/dinokage",
                discordId: "446946428158214164",
                role: "CO-FOUNDER & VP PRODUCT",
                description: "Owns the campus-facing product surface, Registrar dashboards, and welfare module UX.",
                icon: <Users className="h-5 w-5 text-[var(--color-text-secondary)]" />,
                specialty: "code karne wala",
                tech: "FastAPI · NextJS · Redis",
                isAccent: false,
              },
            ].map((member, index) => (
              <TeamMemberCard key={index} member={member} />
            ))}
          </motion.div>
        </motion.div>
      </section>

      <section
        id="contact"
        className="section-gap w-full relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto max-w-2xl"
        >
          <div className="card-surface rounded-xl p-8">
            <span className="section-label text-left block">Get Started</span>
            <h3 className="text-2xl font-bold mb-2 text-[var(--color-text-primary)]">Get in Touch</h3>
            <p className="text-sm mb-6 text-[var(--color-text-secondary)]">
              Interested in implementing Fazri Analyzer for your campus? Contact
              us for a demo.
            </p>
            <form className="space-y-4" onSubmit={(e: FormEvent<HTMLFormElement>) => e.preventDefault()}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label
                    htmlFor="first-name"
                    className="text-sm font-medium text-[var(--color-text-secondary)]"
                  >
                    First name
                  </label>
                  <Input
                    id="first-name"
                    placeholder="Enter your first name"
                    className="input-field"
                  />
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="last-name"
                    className="text-sm font-medium text-[var(--color-text-secondary)]"
                  >
                    Last name
                  </label>
                  <Input
                    id="last-name"
                    placeholder="Enter your last name"
                    className="input-field"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-[var(--color-text-secondary)]"
                >
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  className="input-field"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="institution"
                  className="text-sm font-medium text-[var(--color-text-secondary)]"
                >
                  Institution
                </label>
                <Input
                  id="institution"
                  placeholder="Your institution name"
                  className="input-field"
                />
              </div>
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  type="submit"
                  className="btn-primary w-full"
                >
                  Request Demo
                </Button>
              </motion.div>
            </form>
          </div>
        </motion.div>
      </section>

      <footer className="w-full relative z-10 border-t border-[var(--color-border-default)]">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 py-10 md:px-6 mx-auto"
        >
          <div className="grid gap-8 lg:grid-cols-4">
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Database className="h-6 w-6 text-[var(--color-accent)]" />
                <span className="font-bold text-xl text-[var(--color-text-primary)]">
                  Fazri Analyzer
                </span>
              </div>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Advanced campus entity resolution and security monitoring
                through AI-powered graph analytics.
              </p>
              <div className="flex space-x-3">
                {[
                  { icon: <Github className="h-5 w-5" />, label: "GitHub", url: undefined },
                  { icon: <Linkedin className="h-5 w-5" />, label: "LinkedIn", url: undefined },
                  { icon: <Twitter className="h-5 w-5" />, label: "Twitter", url: undefined },
                ].map((social, index) => social.url ? (
                  <motion.div
                    key={index}
                    whileHover={{ y: -5, scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <a
                      href={social.url}
                      className="social-icon transition-colors"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {social.icon}
                      <span className="sr-only">{social.label}</span>
                    </a>
                  </motion.div>
                ) : null)}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-4 text-[var(--color-text-primary)]">Product</h3>
              <nav className="flex flex-col space-y-2 text-sm">
                <a
                  href="#features"
                  className="footer-link transition-colors"
                >
                  Features
                </a>
                <a
                  href="#architecture"
                  className="footer-link transition-colors"
                >
                  Architecture
                </a>
                <a
                  href="#"
                  className="footer-link transition-colors"
                >
                  Documentation
                </a>
                <a
                  href="#"
                  className="footer-link transition-colors"
                >
                  API Reference
                </a>
              </nav>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-4 text-[var(--color-text-primary)]">Company</h3>
              <nav className="flex flex-col space-y-2 text-sm">
                <a
                  href="#"
                  className="footer-link transition-colors"
                >
                  About
                </a>
                <a
                  href="#team"
                  className="footer-link transition-colors"
                >
                  Team
                </a>
                <a
                  href="#contact"
                  className="footer-link transition-colors"
                >
                  Contact
                </a>
                <a
                  href="#"
                  className="footer-link transition-colors"
                >
                  Privacy
                </a>
                <a
                  href="#"
                  className="footer-link transition-colors"
                >
                  Terms
                </a>
              </nav>
            </div>

            <div>
              <h3 className="text-lg font-medium mb-4 text-[var(--color-text-primary)]">Contact</h3>
              <div className="space-y-2 text-sm text-[var(--color-text-secondary)]">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  <span>noc@rdpdatacenter.in</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  <span>Campus Security Application</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-[var(--color-border-default)]">
            <p className="text-xs text-center text-[var(--color-text-muted)]">
              &copy; {new Date().getFullYear()} Fazri Analyzer. All rights
              reserved.
            </p>
          </div>
        </motion.div>
      </footer>
    </div>
  );
};

export default FazriAnalyzerLanding;
