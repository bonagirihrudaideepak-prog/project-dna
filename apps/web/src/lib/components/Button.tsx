import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn2 } from "../utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "sm" | "md" | "lg";
}

/**
 * Button Component
 * Primary, Secondary, and Tertiary variants with proper states
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = "primary", size = "md", disabled = false, className, onClick, ...otherProps }, ref) => {
    const sizeStyles = {
      sm: "h-8 px-3 text-sm",
      md: "h-10 px-4 text-base",
      lg: "h-12 px-6 text-lg",
    };

    const variantStyles: Record<string, string> = {
      primary:
        "bg-lavenderPrimary text-white hover:bg-lavenderPrimary focus-visible:ring-2 focus-visible:ring-lavenderPrimary",
      secondary:
        "bg-transparent text-slate-600 border border-borderDefault hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-lavenderPrimary",
      outline:
        "bg-transparent text-lavenderPrimary border border-lavenderPrimary hover:bg-lavenderSoft focus-visible:ring-2 focus-visible:ring-lavenderPrimary",
      ghost: "bg-transparent text-slate-600 hover:bg-slate-50",
    };

    const style = variantStyles[variant] || variantStyles.primary;

    return (
      <button
        ref={ref}
        className={cn2(
          "inline-flex items-center justify-center rounded-md transition-colors focus-visible:outline-none",
          style,
          sizeStyles[size],
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
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