/** Minimal multi-agent constellation — agents orbit the human hub; traces flow. */
export function AgentMesh({ className = "" }: { className?: string }) {
  const cx = 520;
  const cy = 360;
  const orbitDur = "48s";

  return (
    <svg
      className={className}
      viewBox="0 0 960 720"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <linearGradient id="trace" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0d7c7c" stopOpacity="0.65" />
          <stop offset="100%" stopColor="#0f1c1f" stopOpacity="0.15" />
        </linearGradient>
        <linearGradient id="wafer" x1="0.2" y1="0" x2="0.9" y2="1">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#e8eef0" />
        </linearGradient>
        <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Static wafer field */}
      <circle cx={cx} cy={cy} r="280" fill="url(#wafer)" stroke="#0f1c1f" strokeOpacity="0.06" />

      {/* Rotating outer assembly */}
      <g>
        <animateTransform
          attributeName="transform"
          type="rotate"
          from={`0 ${cx} ${cy}`}
          to={`360 ${cx} ${cy}`}
          dur={orbitDur}
          repeatCount="indefinite"
        />

        <circle
          cx={cx}
          cy={cy}
          r="220"
          stroke="#0d7c7c"
          strokeOpacity="0.1"
          strokeDasharray="2 10"
          className="mesh-dash-spin"
        />
        <circle cx={cx} cy={cy} r="150" stroke="#0f1c1f" strokeOpacity="0.05" />

        <g stroke="#0f1c1f" strokeOpacity="0.045" strokeWidth="1">
          <path d="M280 220 H760" />
          <path d="M300 360 H740" />
          <path d="M280 500 H760" />
          <path d="M400 140 V580" />
          <path d="M520 120 V600" />
          <path d="M640 140 V580" />
        </g>

        <g stroke="url(#trace)" strokeWidth="1.5" strokeLinecap="round" fill="none">
          <path
            className="mesh-flow"
            style={{ strokeDasharray: "10 14", animationDuration: "2.4s" }}
            d="M360 250 C420 220, 480 220, 520 280"
          />
          <path
            className="mesh-flow"
            style={{ strokeDasharray: "8 12", animationDuration: "2.8s", animationDelay: "-0.6s" }}
            d="M520 280 C560 320, 620 300, 680 250"
          />
          <path
            className="mesh-flow"
            style={{ strokeDasharray: "10 16", animationDuration: "3.2s", animationDelay: "-1.1s" }}
            d="M360 250 C340 340, 360 420, 400 470"
          />
          <path
            className="mesh-flow"
            style={{ strokeDasharray: "9 13", animationDuration: "2.6s", animationDelay: "-0.3s" }}
            d="M680 250 C720 340, 700 420, 640 480"
          />
          <path
            className="mesh-flow"
            style={{ strokeDasharray: "12 14", animationDuration: "3s", animationDelay: "-1.5s" }}
            d="M400 470 C460 520, 580 520, 640 480"
          />
          <path
            className="mesh-flow"
            style={{ strokeDasharray: "6 10", animationDuration: "2.2s", animationDelay: "-0.9s" }}
            d="M520 280 C520 340, 520 400, 520 440"
          />
        </g>

        <AgentNode x={360} y={250} label="SUPPORT" delay="0s" orbitDur={orbitDur} />
        <AgentNode x={680} y={250} label="VENDOR" delay="0.4s" orbitDur={orbitDur} />
        <AgentNode x={400} y={470} label="TRIAGE" delay="0.8s" orbitDur={orbitDur} />
        <AgentNode x={640} y={480} label="REMOTE" delay="1.2s" orbitDur={orbitDur} />

        <g fill="#0d7c7c" fillOpacity="0.35">
          <rect x="448" y="318" width="6" height="6" rx="1" />
          <rect x="586" y="318" width="6" height="6" rx="1" />
          <rect x="448" y="396" width="6" height="6" rx="1" />
          <rect x="586" y="396" width="6" height="6" rx="1" />
        </g>
      </g>

      {/* Human hub stays fixed */}
      <g filter="url(#soft)">
        <circle cx={cx} cy={cy} r="28" fill="#ffffff" stroke="#0d7c7c" strokeWidth="1.5" />
        <circle
          cx={cx}
          cy={cy}
          r="8"
          fill="#0d7c7c"
          className="animate-mesh-pulse"
          style={{ transformOrigin: `${cx}px ${cy}px` }}
        />
      </g>
      <text
        x={cx}
        y={cy + 48}
        textAnchor="middle"
        fill="#0f1c1f"
        fillOpacity="0.45"
        fontSize="11"
        fontFamily="var(--font-sans), system-ui, sans-serif"
        letterSpacing="0.12em"
      >
        HUMAN
      </text>
    </svg>
  );
}

function AgentNode({
  x,
  y,
  label,
  delay,
  orbitDur,
}: {
  x: number;
  y: number;
  label: string;
  delay: string;
  orbitDur: string;
}) {
  return (
    <g>
      <circle cx={x} cy={y} r="22" fill="#ffffff" stroke="#0f1c1f" strokeOpacity="0.12" strokeWidth="1" />
      <circle
        cx={x}
        cy={y}
        r="6"
        fill="#0f1c1f"
        fillOpacity="0.7"
        className="animate-mesh-pulse"
        style={{ animationDelay: delay, transformOrigin: `${x}px ${y}px` }}
      />
      <rect
        x={x - 10}
        y={y - 10}
        width="20"
        height="20"
        rx="3"
        stroke="#0d7c7c"
        strokeOpacity="0.35"
        strokeWidth="1"
        fill="none"
      />
      {/* Counter-rotate labels so they stay upright */}
      <g>
        <animateTransform
          attributeName="transform"
          type="rotate"
          from={`0 ${x} ${y}`}
          to={`-360 ${x} ${y}`}
          dur={orbitDur}
          repeatCount="indefinite"
        />
        <text
          x={x}
          y={y + 38}
          textAnchor="middle"
          fill="#0f1c1f"
          fillOpacity="0.4"
          fontSize="10"
          fontFamily="var(--font-sans), system-ui, sans-serif"
          letterSpacing="0.14em"
        >
          {label}
        </text>
      </g>
    </g>
  );
}
