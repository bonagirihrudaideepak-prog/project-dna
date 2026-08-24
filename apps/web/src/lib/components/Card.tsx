import { forwardRef, type HTMLAttributes } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  shadow?: "sm" | "md" | "lg";
}

/**
 * Card Component (design tokens per "UI_UX Design Overview").
 * White panel, 1px slate-200 border, rounded-xl, subtle shadow.
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, style, shadow = "sm", ...otherProps }, ref) => {
    const shadowStyles: Record<string, string> = {
      sm: "0 1px 3px rgba(0,0,0,0.04)",
      md: "0 4px 16px rgba(99,102,241,0.06)",
      lg: "0 10px 15px rgba(0,0,0,0.08)",
    };

    return (
      <div
        ref={ref}
        className={className}
        style={{
          backgroundColor: "#ffffff",
          border: "1px solid #e2e8f0",
          borderRadius: "12px",
          boxShadow: shadowStyles[shadow],
          ...style,
        }}
        {...otherProps}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export default Card;
