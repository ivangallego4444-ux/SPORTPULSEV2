const RING_CONFIGS = [
  { nodes: 8, radius: 76, duration: "10s", axis: "Y", color: "bg-neon-emerald", glow: "rgba(0,255,136,0.75)" },
  { nodes: 6, radius: 58, duration: "7s", axis: "X", color: "bg-neon-cyan", glow: "rgba(0,240,255,0.75)", reverse: true },
  { nodes: 5, radius: 95, duration: "16s", axis: "Z", color: "bg-neon-purple", glow: "rgba(168,85,247,0.7)" },
];

const PARTICLES = Array.from({ length: 10 }).map((_, i) => ({
  left: 8 + ((i * 37) % 85),
  top: 8 + ((i * 53) % 85),
  delay: (i % 5) * 0.6,
  duration: 3 + (i % 4),
}));

function Ring({
  nodes,
  radius,
  duration,
  axis,
  color,
  glow,
  reverse,
}: {
  nodes: number;
  radius: number;
  duration: string;
  axis: "X" | "Y" | "Z";
  color: string;
  glow: string;
  reverse?: boolean;
}) {
  return (
    <div
      className="absolute inset-0"
      style={{
        transformStyle: "preserve-3d",
        animation: `orbit-${axis} ${duration} linear infinite ${reverse ? "reverse" : ""}`,
      }}
    >
      {Array.from({ length: nodes }).map((_, i) => {
        const angle = (360 / nodes) * i;
        const transform =
          axis === "Y"
            ? `rotateY(${angle}deg) translateZ(${radius}px)`
            : axis === "X"
              ? `rotateX(${angle}deg) translateZ(${radius}px)`
              : `rotateZ(${angle}deg) translateX(${radius}px)`;
        return (
          <div
            key={i}
            className={`absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ${color}`}
            style={{ transform, boxShadow: `0 0 10px 3px ${glow}` }}
          />
        );
      })}
    </div>
  );
}

/** Hyperrealistic multi-ring 3D holographic core: three independent rings
 * orbiting on different axes (X/Y/Z) at different speeds, plus floating
 * neon particles — all real CSS 3D transforms (perspective + rotate +
 * translateZ), no WebGL/Three.js. */
export default function NeuralCore3D() {
  return (
    <div className="relative mx-auto h-52 w-52" style={{ perspective: "1400px" }}>
      {PARTICLES.map((p, i) => (
        <div
          key={i}
          className="absolute h-1 w-1 rounded-full bg-neon-cyan/70"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            animation: `float-particle ${p.duration}s ease-in-out infinite`,
            animationDelay: `${p.delay}s`,
            boxShadow: "0 0 6px 2px rgba(0,240,255,0.6)",
          }}
        />
      ))}

      {RING_CONFIGS.map((ring, i) => (
        <Ring key={i} {...ring} axis={ring.axis as "X" | "Y" | "Z"} />
      ))}

      <div className="absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-neon-emerald via-neon-cyan to-neon-purple opacity-70 blur-lg" />
      <div className="absolute left-1/2 top-1/2 h-7 w-7 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-[0_0_28px_8px_rgba(0,255,136,0.6)]" />
    </div>
  );
}
