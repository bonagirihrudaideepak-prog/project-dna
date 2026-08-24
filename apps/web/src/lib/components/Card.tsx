import { forwardRef, type HTMLAttributes } from "react";
import { cn2 } from "../utils";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  shadow?: "sm" | "md" | "lg";
  bg?: "white" | "lavenderSoft";
}

/**
 * Card Component
 * Reusable card with proper spacing and border radius
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, shadow = "md", bg = "white", ...otherProps }, ref) => {
    const bgClass = bg === "lavenderSoft" ? "bg-lavenderSoft" : "bg-white";
    const shadowClass = shadow === "lg" ? "shadow-lg" : shadow === "sm" ? "shadow-sm" : "shadow-md";

    return (
      <div
        ref={ref}
        className={cn2("rounded-md p-4 border border-borderDefault", bgClass, shadowClass, className)}
        {...otherProps}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export default Card;