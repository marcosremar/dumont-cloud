import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"
import { cn } from "../../lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        // Primary/Default - Verde (#4caf50) - Padrão para ações principais
        // Alinhado com tailadmin-ui Button
        default:
          "bg-[#4caf50] text-white font-semibold shadow-lg hover:bg-[#43a047] rounded-xl transition-all",
        primary:
          "bg-[#4caf50] text-white font-semibold shadow-lg hover:bg-[#43a047] rounded-xl transition-all",
        success:
          "bg-[#4caf50] text-white font-semibold shadow-lg hover:bg-[#43a047] rounded-xl transition-all",

        // Brand - Cor da marca (roxo) para casos específicos
        brand:
          "bg-brand-500 text-white font-bold shadow hover:bg-brand-600 rounded-lg transition-all",

        // Warning - Yellow/Amber (atenção)
        warning:
          "bg-amber-500 text-white font-medium shadow hover:bg-amber-600 disabled:bg-amber-700 rounded-lg transition-all",

        // Danger - Red (ação destrutiva)
        danger:
          "bg-red-600 text-white font-medium shadow hover:bg-red-700 disabled:bg-red-800 rounded-lg transition-all",
        destructive:
          "bg-red-600 text-white font-medium shadow hover:bg-red-700 disabled:bg-red-800 rounded-lg transition-all",

        // Info - Blue (informação)
        info:
          "bg-blue-600 text-white font-medium shadow hover:bg-blue-700 disabled:bg-blue-800 rounded-lg transition-all",

        // Outline variants
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        "outline-success":
          "border border-green-500 text-green-500 bg-transparent hover:bg-green-500/10 rounded-lg transition-all",
        "outline-warning":
          "border border-amber-500 text-amber-500 bg-transparent hover:bg-amber-500/10 rounded-lg transition-all",
        "outline-danger":
          "border border-red-500 text-red-500 bg-transparent hover:bg-red-500/10 rounded-lg transition-all",
        "outline-info":
          "border border-blue-500 text-blue-500 bg-transparent hover:bg-blue-500/10 rounded-lg transition-all",

        // Secondary and utility
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost:
          "hover:bg-accent hover:text-accent-foreground",
        link:
          "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        xl: "h-12 rounded-lg px-10 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(
  ({
    className,
    variant,
    size,
    asChild = false,
    icon: Icon,
    iconPosition = 'left',
    loading = false,
    children,
    disabled,
    ...props
  }, ref) => {
    const Comp = asChild ? Slot : "button"

    // Determine icon size based on button size
    const iconSize = size === 'sm' ? 14 : size === 'lg' || size === 'xl' ? 20 : 16

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {Icon && iconPosition === 'left' && !loading && <Icon size={iconSize} />}
        {children}
        {Icon && iconPosition === 'right' && !loading && <Icon size={iconSize} />}
      </Comp>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
