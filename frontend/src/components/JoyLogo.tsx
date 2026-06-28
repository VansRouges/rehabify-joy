export function JoyLogo({ size = "md" }: { size?: "sm" | "md" }) {
  const iconSize = size === "sm" ? "h-7 w-7" : "h-8 w-8";
  const textSize = size === "sm" ? "text-lg" : "text-xl";

  return (
    <div className="flex items-center gap-2.5">
      <div className={`${iconSize} relative shrink-0`}>
        <div className="absolute inset-0 rounded-full bg-joy-peach-light opacity-80" />
        <div className="absolute inset-0 rounded-full bg-joy-green opacity-90 mix-blend-multiply" />
        <div className="absolute inset-[3px] rounded-full border-2 border-white/30" />
      </div>
      <div className="leading-tight">
        <span className={`font-serif font-semibold text-joy-green ${textSize}`}>Joy.</span>
        <span className="ml-1.5 text-[10px] font-medium uppercase tracking-widest text-joy-text-muted">
          by Rehabify
        </span>
      </div>
    </div>
  );
}
