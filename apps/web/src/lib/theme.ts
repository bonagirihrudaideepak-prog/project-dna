/*
 * Project DNA - Design System Tokens
 * Based on UI/UX Design Overview
 * Colors: Lavender/Soft Pink/White light theme
*/

export const tokens = {
  colors: {
    // Primary palette
    lavenderPrimary: "#6B46C1",
    lavenderSoft: "#EDE9F2",
    pinkSoft: "#F87171",
    
    // Semantic colors
    success: "#10B981",
    warning: "#F59E0B",
    error: "#EF4444",
    
    // Slate gray palette
    slate50: "#F8FAFC",
    slate100: "#F1F5F9",
    slate600: "#475569",
    slate700: "#1E293B",
    slate500: "#64748B",
    slate400: "#94A3B8",
    
    // Backgrounds
    white: "#FFFFFF",
    defaultBg: "#FFFFFF",
    pageBg: "#F8FAFC",
    
    // Borders
    borderDefault: "#D1D5DB",
    borderLight: "#E5E7EB",
    
    // Feedback colors
    info: "#3B82F6",
    
    // Transparent/Opacity
    whiteAlpha: "rgba(255, 255, 255, 0.8)",
    blackAlpha: "rgba(0, 0, 0, 0.4)",
  },
  
  typography: {
    fontFamily: "'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
    fontSize: {
      xs: "0.75rem",
      sm: "0.875rem",
      md: "1rem",
      lg: "1.125rem",
      xl: "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem",
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      none: "1",
      tighter: "1.25",
      relaxed: "1.5",
      default: "1.5",
    },
  },
  
  spacing: {
    1: "0.25rem",   // 4px
    2: "0.5rem",    // 8px
    3: "0.75rem",   // 12px
    4: "1rem",      // 16px
    5: "1.5rem",    // 24px
    6: "2rem",      // 32px",
    8: "32px",
  },
  
  radius: {
    sm: "0.375rem",   // 6px
    md: "0.5rem",     // 8px
    lg: "0.75rem",    // 12px
    full: "9999px",
  },
  
  shadow: {
    sm: "0 1px 2px rgba(0, 0, 0, 0.05)",
    md: "0 4px 6px rgba(0, 0, 0, 0.03)",
    lg: "0 10px 15px rgba(0, 0, 0, 0.1)",
    xl: "0 20px 25px rgba(0, 0, 0, 0.1)",
  },
  
  breakpoints: {
    sm: "@media (min-width: 640px)",
    md: "@media (min-width: 768px)",
    lg: "@media (min-width: 1024px)",
    xl: "@media (min-width: 1280px)",
  },
};