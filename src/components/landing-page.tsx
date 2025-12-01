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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
// import Link from "next/link";
import { useSession } from "next-auth/react";
// import { redirect } from "next/navigation";
import { useRouter } from "next/navigation";

function cn(...classes: (string | undefined | null | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

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

interface Dot {
  x: number;
  y: number;
  baseColor: string;
  targetOpacity: number;
  currentOpacity: number;
  opacitySpeed: number;
  baseRadius: number;
  currentRadius: number;
}

const FazriAnalyzerLanding: React.FC = () => {
    const { data: session } = useSession();
    const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameId = useRef<number | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isScrolled, setIsScrolled] = useState<boolean>(false);

  const { scrollY } = useScroll();
  useMotionValueEvent(scrollY, "change", (latest) => {
    setIsScrolled(latest > 10);
  });

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
          baseColor: `rgba(16, 185, 129, ${BASE_OPACITY_MAX})`,
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

      const colorMatch = dot.baseColor.match(
        /rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/
      );
      const r = colorMatch ? colorMatch[1] : "16";
      const g = colorMatch ? colorMatch[2] : "185";
      const b = colorMatch ? colorMatch[3] : "129";

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
    BASE_RADIUS,
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
      backgroundColor: "rgba(17, 17, 17, 0.8)",
      borderBottomColor: "rgba(55, 65, 81, 0.5)",
      position: "fixed",
      boxShadow: "none",
    },
    scrolled: {
      backgroundColor: "rgba(17, 17, 17, 0.95)",
      borderBottomColor: "rgba(75, 85, 99, 0.7)",
      boxShadow:
        "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
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

  const itemFadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 },
    },
  };

  return (
    <div className="pt-[100px] relative bg-[#111111] text-gray-300 min-h-screen flex flex-col">
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-0 pointer-events-none opacity-80"
      />
      <div
        className="absolute inset-0 z-1 pointer-events-none"
        style={{
          background:
            "linear-gradient(to bottom, transparent 0%, #111111 90%), radial-gradient(ellipse at center, transparent 40%, #111111 95%)",
        }}
      ></div>

      <motion.header
        variants={headerVariants}
        initial="top"
        animate={isScrolled ? "scrolled" : "top"}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="px-6 w-full md:px-10 lg:px-16 sticky top-0 z-30 backdrop-blur-md border-b"
      >
        <nav className="flex justify-between items-center max-w-screen-xl mx-auto h-[70px]">
          <div className="flex items-center flex-shrink-0">
            <Database className="h-6 w-6 text-emerald-500" />
            <span className="text-xl font-bold text-white ml-2">
              Fazri Analyzer
            </span>
          </div>

          <div className="hidden md:flex items-center justify-center flex-grow space-x-6 lg:space-x-8 px-4">
            <a
              href="#features"
              className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
            >
              Features
            </a>
            <a
              href="#architecture"
              className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
            >
              Architecture
            </a>
            <a
              href="#security"
              className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
            >
              Security
            </a>
            <a
              href="#contact"
              className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
            >
              Contact
            </a>
          </div>

          <div className="flex items-center flex-shrink-0 space-x-4 lg:space-x-6">
            <Button className="group relative overflow-hidden" size="lg" onClick={() => router.push('/dashboard')}>
              <span className="mr-8 transition-opacity duration-500 group-hover:opacity-0">
                {session ? "Dashboard" : "Sign in"}
              </span>
              <i className="absolute right-1 top-1 bottom-1 rounded-sm z-10 grid w-1/4 place-items-center transition-all duration-500 bg-primary-foreground/15 group-hover:w-[calc(100%-0.5rem)] group-active:scale-95">
                <ChevronRight size={16} strokeWidth={2} aria-hidden="true" />
              </i>
            </Button>

            <motion.button
              className="md:hidden text-gray-300 hover:text-white z-50"
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
              className="md:hidden absolute top-full left-0 right-0 bg-[#111111]/95 backdrop-blur-sm shadow-lg py-4 border-t border-gray-800/50"
            >
              <div className="flex flex-col items-center space-y-4 px-6">
                <a
                  href="#features"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
                >
                  Features
                </a>
                <a
                  href="#architecture"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
                >
                  Architecture
                </a>
                <a
                  href="#security"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
                >
                  Security
                </a>
                <a
                  href="#contact"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
                >
                  Contact
                </a>
                <hr className="w-full border-t border-gray-700/50 my-2" />
                <a
                  href="#signin"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="text-sm font-medium text-gray-300 hover:text-white transition-colors duration-200"
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
          <span className="bg-[#1a1a1a] border border-gray-700 text-emerald-500 px-4 py-1 rounded-full text-xs sm:text-sm font-medium cursor-pointer hover:border-emerald-500/50 transition-colors inline-flex items-center gap-2">
            <Shield className="h-3 w-3" />
            Advanced Entity Resolution & Security Monitoring
          </span>
        </motion.div>

        <motion.h1
          variants={headlineVariants}
          initial="hidden"
          animate="visible"
          className="text-4xl sm:text-5xl lg:text-[64px] font-semibold text-white leading-tight max-w-4xl mb-4"
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
              mainClassName="text-emerald-500 mx-1"
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
          className="text-base sm:text-lg lg:text-xl text-gray-400 max-w-2xl mx-auto mb-8"
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
            className="flex-grow w-full sm:w-auto px-4 py-2 rounded-md bg-[#2a2a2a] border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
          />
          <motion.button
            type="submit"
            className="w-full sm:w-auto bg-emerald-500 text-[#111111] px-5 py-2 rounded-md text-sm font-semibold hover:bg-emerald-400 transition-colors duration-200 whitespace-nowrap shadow-sm hover:shadow-md flex-shrink-0"
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
        className="w-full py-12 md:py-24 lg:py-32 relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto"
        >
          <div className="flex flex-col items-center justify-center space-y-4 text-center mb-12">
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl text-white"
            >
              Core Features
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mx-auto max-w-[900px] text-gray-400 md:text-xl"
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
                icon: <Database className="h-10 w-10 text-emerald-500" />,
                title: "Entity Resolution",
                description:
                  "Multi-modal fusion with confidence scoring for accurate entity identification and linking across campus systems.",
              },
              {
                icon: <Network className="h-10 w-10 text-emerald-500" />,
                title: "Graph Analytics",
                description:
                  "Neo4j-powered relationship mapping for entity linking, gap detection, and pattern recognition.",
              },
              {
                icon: <Brain className="h-10 w-10 text-emerald-500" />,
                title: "Predictive AI",
                description:
                  "LSTM and XGBoost models for location prediction and anomaly detection with explainable results.",
              },
              {
                icon: <Shield className="h-10 w-10 text-emerald-500" />,
                title: "Security Monitoring",
                description:
                  "Real-time anomaly detection and predictive monitoring using ML models trained on campus activity data.",
              },
              {
                icon: <Activity className="h-10 w-10 text-emerald-500" />,
                title: "Timeline Generation",
                description:
                  "Graph-based timeline visualization for tracking entity movements and interactions over time.",
              },
              {
                icon: <Lock className="h-10 w-10 text-emerald-500" />,
                title: "OAuth & JWT Auth",
                description:
                  "Secure authentication and authorization with Prisma ORM for user data management.",
              },
            ].map((feature, index) => (
              <motion.div
                key={index}
                variants={itemFadeIn}
                whileHover={{ y: -10, transition: { duration: 0.3 } }}
                className="group relative overflow-hidden rounded-xl border border-gray-700 p-6 shadow-sm transition-all hover:shadow-md bg-[#1a1a1a]/80 hover:border-emerald-500/50"
              >
                <div className="space-y-3">
                  <div className="mb-4">{feature.icon}</div>
                  <h3 className="text-xl font-bold text-white">
                    {feature.title}
                  </h3>
                  <p className="text-gray-400">{feature.description}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <section
        id="architecture"
        className="w-full py-12 md:py-24 lg:py-32 relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto"
        >
          <div className="flex flex-col items-center justify-center space-y-4 text-center mb-12">
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl text-white"
            >
              System Architecture
            </motion.h2>
          </div>

          <div className="mx-auto max-w-5xl grid gap-6 sm:grid-cols-5">
            <Card className="group overflow-hidden shadow-black/5 sm:col-span-3 bg-[#1a1a1a] border-gray-700">
              <CardHeader>
                <div className="md:p-6">
                  <p className="font-medium text-white">
                    Next.js Frontend on Vercel
                  </p>
                  <p className="text-gray-400 mt-3 max-w-sm text-sm">
                    Interactive dashboard for entity queries, timeline
                    visualization, and anomaly monitoring with SSR and edge
                    caching.
                  </p>
                </div>
              </CardHeader>
              <CardContent className="relative h-fit pl-6 md:pl-12">
                <div className="bg-[#111111] overflow-hidden rounded-tl-lg border-l border-t border-gray-700 pl-2 pt-2">
                  <div className="aspect-video bg-gradient-to-br from-emerald-500/20 to-transparent rounded flex items-center justify-center">
                    <Users className="h-16 w-16 text-emerald-500" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="group overflow-hidden shadow-zinc-950/5 sm:col-span-2 bg-[#1a1a1a] border-gray-700">
              <p className="mx-auto my-6 max-w-md text-balance px-6 text-center text-lg font-semibold sm:text-2xl text-white">
                FastAPI Backend
              </p>
              <CardContent className="mt-auto h-fit">
                <div className="relative mb-6 sm:mb-0">
                  <div className="aspect-square overflow-hidden rounded-r-lg border border-gray-700 bg-gradient-to-br from-emerald-500/20 to-transparent flex items-center justify-center">
                    <Zap className="h-12 w-12 text-emerald-500" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="group p-6 shadow-black/5 sm:col-span-2 md:p-12 bg-[#1a1a1a] border-gray-700">
              <p className="mx-auto mb-12 max-w-md text-balance text-center text-lg font-semibold sm:text-2xl text-white">
                Neo4j Graph Database
              </p>
              <div className="flex justify-center">
                <div className="bg-gradient-to-br from-emerald-500/20 to-transparent flex aspect-square size-24 items-center justify-center rounded-lg border border-gray-700 p-3 shadow-lg">
                  <Network className="size-12 text-emerald-500" />
                </div>
              </div>
            </Card>

            <Card className="group relative shadow-black/5 sm:col-span-3 bg-[#1a1a1a] border-gray-700">
              <CardHeader className="p-6 md:p-12">
                <p className="font-medium text-white">ML Prediction Models</p>
                <p className="text-gray-400 mt-2 max-w-sm text-sm">
                  TensorFlow LSTM and XGBoost for location prediction with
                  explainable AI.
                </p>
              </CardHeader>
              <CardContent className="relative h-fit px-6 pb-6 md:px-12 md:pb-12">
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-gradient-to-br from-emerald-500/20 to-transparent flex aspect-square items-center justify-center border border-gray-700 rounded p-4">
                    <Brain className="size-8 text-emerald-500" />
                  </div>
                  <div className="aspect-square border border-dashed border-gray-700 rounded"></div>
                  <div className="bg-gradient-to-br from-emerald-500/20 to-transparent flex aspect-square items-center justify-center border border-gray-700 rounded p-4">
                    <Activity className="size-8 text-emerald-500" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </section>

      <section
        id="contact"
        className="w-full py-12 md:py-24 lg:py-32 relative z-10"
      >
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
          className="container px-4 md:px-6 mx-auto max-w-2xl"
        >
          <div className="rounded-xl border border-gray-700 bg-[#1a1a1a]/80 p-8 shadow-sm">
            <h3 className="text-2xl font-bold text-white mb-2">Get in Touch</h3>
            <p className="text-sm text-gray-400 mb-6">
              Interested in implementing Fazri Analyzer for your campus? Contact
              us for a demo.
            </p>
            <form className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label
                    htmlFor="first-name"
                    className="text-sm font-medium text-gray-300"
                  >
                    First name
                  </label>
                  <Input
                    id="first-name"
                    placeholder="Enter your first name"
                    className="bg-[#2a2a2a] border-gray-700 text-white"
                  />
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="last-name"
                    className="text-sm font-medium text-gray-300"
                  >
                    Last name
                  </label>
                  <Input
                    id="last-name"
                    placeholder="Enter your last name"
                    className="bg-[#2a2a2a] border-gray-700 text-white"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-gray-300"
                >
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  className="bg-[#2a2a2a] border-gray-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="institution"
                  className="text-sm font-medium text-gray-300"
                >
                  Institution
                </label>
                <Input
                  id="institution"
                  placeholder="Your institution name"
                  className="bg-[#2a2a2a] border-gray-700 text-white"
                />
              </div>
              <motion.div
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  type="submit"
                  className="w-full bg-emerald-500 hover:bg-emerald-400 text-[#111111]"
                >
                  Request Demo
                </Button>
              </motion.div>
            </form>
          </div>
        </motion.div>
      </section>

      <footer className="w-full border-t border-gray-700 relative z-10">
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
                <Database className="h-6 w-6 text-emerald-500" />
                <span className="font-bold text-xl text-white">
                  Fazri Analyzer
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Advanced campus entity resolution and security monitoring
                through AI-powered graph analytics.
              </p>
              <div className="flex space-x-3">
                {[
                  { icon: <Github className="h-5 w-5" />, label: "GitHub" },
                  { icon: <Linkedin className="h-5 w-5" />, label: "LinkedIn" },
                  { icon: <Twitter className="h-5 w-5" />, label: "Twitter" },
                ].map((social, index) => (
                  <motion.div
                    key={index}
                    whileHover={{ y: -5, scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <a
                      href="#"
                      className="text-gray-400 hover:text-emerald-500 transition-colors"
                    >
                      {social.icon}
                      <span className="sr-only">{social.label}</span>
                    </a>
                  </motion.div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-medium text-white mb-4">Product</h3>
              <nav className="flex flex-col space-y-2 text-sm">
                <a
                  href="#features"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  Features
                </a>
                <a
                  href="#architecture"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  Architecture
                </a>
                <a
                  href="#"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  Documentation
                </a>
                <a
                  href="#"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  API Reference
                </a>
              </nav>
            </div>

            <div>
              <h3 className="text-lg font-medium text-white mb-4">Company</h3>
              <nav className="flex flex-col space-y-2 text-sm">
                <a
                  href="#"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  About
                </a>
                <a
                  href="#contact"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  Contact
                </a>
                <a
                  href="#"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  Privacy
                </a>
                <a
                  href="#"
                  className="text-gray-400 hover:text-emerald-500 transition-colors"
                >
                  Terms
                </a>
              </nav>
            </div>

            <div>
              <h3 className="text-lg font-medium text-white mb-4">Contact</h3>
              <div className="space-y-2 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  <span>noc@rdpdatacenter.in</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  <span>Campus Security Division</span>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-700 mt-8 pt-6">
            <p className="text-xs text-gray-500 text-center">
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
