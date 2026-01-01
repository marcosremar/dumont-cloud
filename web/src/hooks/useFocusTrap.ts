import { useEffect, useRef, RefObject } from "react";

/**
 * CSS selector for all focusable elements within a container.
 * Matches interactive elements that can receive keyboard focus.
 */
export const FOCUSABLE_SELECTOR = [
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "a[href]",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

/**
 * Gets all focusable elements within a container element.
 * @param container - The container element to search within
 * @returns An array of focusable HTML elements
 */
const getFocusableElements = (container: HTMLElement): HTMLElement[] => {
  const elements = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
  return Array.from(elements).filter(
    (el) => el.offsetParent !== null && !el.hasAttribute("disabled")
  );
};

/**
 * A React hook that implements focus trapping for modal components.
 *
 * Features:
 * - Stores the previously focused element when activated
 * - Traps Tab/Shift+Tab within the container
 * - Wraps focus from last to first element and vice versa
 * - Returns focus to the trigger element on cleanup
 *
 * @param containerRef - A ref to the container element to trap focus within
 * @param isActive - Whether the focus trap is currently active
 *
 * @example
 * ```tsx
 * const dialogRef = useRef<HTMLDivElement>(null);
 * useFocusTrap(dialogRef, isOpen);
 *
 * return <div ref={dialogRef}>{children}</div>;
 * ```
 */
export const useFocusTrap = (
  containerRef: RefObject<HTMLElement | null>,
  isActive: boolean
): void => {
  // Store the element that was focused before the trap was activated
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive) return;

    const container = containerRef.current;
    if (!container) return;

    // Store the currently focused element before moving focus
    previouslyFocusedRef.current = document.activeElement as HTMLElement;

    // Focus the first focusable element in the container
    const focusableElements = getFocusableElements(container);
    if (focusableElements.length > 0) {
      // Small delay to ensure the container is rendered
      requestAnimationFrame(() => {
        focusableElements[0]?.focus();
      });
    } else {
      // If no focusable elements, focus the container itself
      container.setAttribute("tabindex", "-1");
      container.focus();
    }

    /**
     * Handle keyboard events to trap focus within the container.
     * - Tab: Move to next focusable element, wrap to first if at end
     * - Shift+Tab: Move to previous focusable element, wrap to last if at start
     */
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;

      const focusable = getFocusableElements(container);
      if (focusable.length === 0) return;

      const firstElement = focusable[0];
      const lastElement = focusable[focusable.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey) {
        // Shift+Tab: moving backwards
        if (activeElement === firstElement || !container.contains(activeElement)) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: moving forwards
        if (activeElement === lastElement || !container.contains(activeElement)) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    // Add the keyboard event listener
    document.addEventListener("keydown", handleKeyDown);

    // Cleanup function: remove listener and return focus
    return () => {
      document.removeEventListener("keydown", handleKeyDown);

      // Return focus to the previously focused element
      if (
        previouslyFocusedRef.current &&
        typeof previouslyFocusedRef.current.focus === "function"
      ) {
        previouslyFocusedRef.current.focus();
      }
    };
  }, [isActive, containerRef]);
};

export default useFocusTrap;
