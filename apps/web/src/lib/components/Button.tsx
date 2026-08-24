import { forwardRef, type ButtonHTMLAttributes } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
}

/**
 * Button Component (design tokens per "UI_UX Design Overview").
 * Primary lavender, secondary/outline white-on-slate-border, ghost transparent.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = "primary", size = "md", disabled = false, className, style, onClick, ...otherProps }, ref) => {
    const sizeStyles: Record<string, React.CSSProperties> = {
      sm: { padding: "6px 12px", fontSize: "12px" },
      md: { padding: "8px 16px", fontSize: "13px" },
      lg: { padding: "10px 22px", fontSize: "14px", fontWeight: 600 },
    };

    const variantStyles: Record<string, React.CSSProperties> = {
      primary: { backgroundColor: disabled ? "#c7d2fe" : "#6366f1", color: "#ffffff", border: "none" },
      secondary: { backgroundColor: "#ffffff", color: "#475569", border: "1px solid #e2e8f0" },
      outline: { backgroundColor: "#ffffff", color: "#6366f1", border: "1px solid #c7d2fe" },
      ghost: { backgroundColor: "transparent", color: "#64748b", border: "none" },
    };

    return (
      <button
        ref={ref}
        className={className}
        style={{
          borderRadius: "8px",
          fontWeight: 500,
          cursor: disabled ? "not-allowed" : "pointer",
          transition: "all 0.15s",
          opacity: disabled ? 0.7 : 1,
          ...variantStyles[variant],
          ...sizeStyles[size],
          ...style,
        }}
        onClick={(e) => {
          if (!disabled) onClick?.(e);
        }}
        disabled={disabled}
        {...otherProps}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
