import { useEffect, useCallback, useRef, RefObject } from "react";

export interface UseFocusTrapOptions {
  /** Whether the focus trap is active */
  isOpen: boolean;
  /** Callback when Escape key is pressed */
  onClose?: () => void;
  /** Optional ref to element that should receive initial focus */
  initialFocusRef?: RefObject<HTMLElement>;
}

/**
 * Selector for all focusable elements within a container.
 * Includes buttons, inputs, selects, textareas, links with href,
 * and elements with tabindex >= 0.
 */
const FOCUSABLE_SELECTOR = [
  'button:not([disabled]):not([tabindex="-1"])',
  'input:not([disabled]):not([type="hidden"]):not([tabindex="-1"])',
  'select:not([disabled]):not([tabindex="-1"])',
  'textarea:not([disabled]):not([tabindex="-1"])',
  'a[href]:not([tabindex="-1"])',
  '[tabindex]:not([tabindex="-1"]):not([disabled])',
  '[contenteditable="true"]:not([tabindex="-1"])',
].join(", ");

/**
 * Gets all focusable elements within a container, filtered by visibility.
 * @param container - The container element to search within
 * @returns Array of focusable HTMLElements
 */
const getFocusableElements = (
  container: HTMLElement | null
): HTMLElement[] => {
  if (!container) return [];

  const elements = Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
  );

  // Filter out elements that are not visible or have zero dimensions
  return elements.filter((el) => {
    // Check if element is visible
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") {
      return false;
    }

    // Check if element has dimensions (not hidden with width/height 0)
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) {
      return false;
    }

    return true;
  });
};

/**
 * Hook that traps focus within a container element when open.
 * Implements WCAG 2.4.3 Focus Order for modal dialogs.
 *
 * @param containerRef - Ref to the container element that should trap focus
 * @param options - Configuration options for the focus trap
 */
export const useFocusTrap = (
  containerRef: RefObject<HTMLElement>,
  options: UseFocusTrapOptions
): void => {
  const { isOpen, onClose, initialFocusRef } = options;

  /**
   * Handles keyboard events for focus trapping.
   * Traps Tab and Shift+Tab to cycle within focusable elements.
   */
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const container = containerRef.current;
      if (!container) return;

      if (event.key === "Tab") {
        const focusableElements = getFocusableElements(container);

        if (focusableElements.length === 0) {
          // No focusable elements, prevent Tab from escaping
          event.preventDefault();
          return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        const activeElement = document.activeElement as HTMLElement;

        if (event.shiftKey) {
          // Shift+Tab: Moving backward
          if (
            activeElement === firstElement ||
            !container.contains(activeElement)
          ) {
            // At first element or focus outside container, wrap to last
            event.preventDefault();
            lastElement.focus();
          }
        } else {
          // Tab: Moving forward
          if (
            activeElement === lastElement ||
            !container.contains(activeElement)
          ) {
            // At last element or focus outside container, wrap to first
            event.preventDefault();
            firstElement.focus();
          }
        }
      }

      // Escape key handler will be implemented in subtask 1.5
    },
    [containerRef]
  );

  /**
   * Handles focus events to prevent focus from escaping the dialog.
   * If focus moves outside the container, redirect it back inside.
   */
  const handleFocusIn = useCallback(
    (event: FocusEvent) => {
      const container = containerRef.current;
      if (!container) return;

      const target = event.target as HTMLElement;

      // If focus moved outside the container, redirect it back
      if (!container.contains(target)) {
        event.preventDefault();
        event.stopPropagation();

        const focusableElements = getFocusableElements(container);
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        } else {
          // If no focusable elements, focus the container itself
          container.focus();
        }
      }
    },
    [containerRef]
  );

  useEffect(() => {
    if (!isOpen) return;

    const container = containerRef.current;
    if (!container) return;

    // Ensure container can receive focus if it has no focusable children
    if (!container.hasAttribute("tabindex")) {
      container.setAttribute("tabindex", "-1");
    }

    // Add event listeners for focus trapping
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("focusin", handleFocusIn);

    // Cleanup function
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("focusin", handleFocusIn);
    };
  }, [isOpen, containerRef, handleKeyDown, handleFocusIn]);

  // Ref to track animation frame IDs for cleanup
  const animationFrameRef = useRef<{ outer: number; inner: number } | null>(
    null
  );

  // Ref to store the previously focused element for focus restoration on close
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);

  /**
   * Auto-focus initial element when dialog opens.
   * Captures the previously focused element for restoration on close.
   * Uses requestAnimationFrame to wait for any opening animations to complete.
   * Priority: initialFocusRef > first focusable element > container
   */
  useEffect(() => {
    if (!isOpen) return;

    const container = containerRef.current;
    if (!container) return;

    // Capture the currently focused element before moving focus to the dialog
    // This allows us to restore focus when the dialog closes
    previouslyFocusedElementRef.current =
      document.activeElement as HTMLElement | null;

    // Use requestAnimationFrame to wait for animation frame after render
    // This ensures the dialog is fully visible before focusing
    const outerId = requestAnimationFrame(() => {
      // Double RAF for better animation timing - ensures styles are applied
      const innerId = requestAnimationFrame(() => {
        // Priority 1: Focus custom initialFocusRef if provided
        if (initialFocusRef?.current) {
          initialFocusRef.current.focus();
          return;
        }

        // Priority 2: Focus first focusable element
        const focusableElements = getFocusableElements(container);
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
          return;
        }

        // Priority 3: Focus the container itself if no focusable elements
        container.focus();
      });

      // Store inner frame ID for cleanup
      if (animationFrameRef.current) {
        animationFrameRef.current.inner = innerId;
      }
    });

    // Track animation frame IDs for cleanup
    animationFrameRef.current = { outer: outerId, inner: 0 };

    // Cleanup function - cancel animation frames if component unmounts before focus
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current.outer);
        if (animationFrameRef.current.inner) {
          cancelAnimationFrame(animationFrameRef.current.inner);
        }
        animationFrameRef.current = null;
      }
    };
  }, [isOpen, containerRef, initialFocusRef]);

  /**
   * Restore focus to the previously focused element when dialog closes.
   * Handles the case where the element no longer exists in the DOM.
   */
  useEffect(() => {
    // This effect only handles focus restoration when dialog closes
    // We need to track the previous isOpen state to detect close
    if (isOpen) {
      // Dialog is open, nothing to do here
      return;
    }

    // Dialog is closed (or was never open) - restore focus if we have a stored element
    const previousElement = previouslyFocusedElementRef.current;

    if (previousElement) {
      // Use requestAnimationFrame to ensure the dialog has fully closed
      // and the element is ready to receive focus
      requestAnimationFrame(() => {
        // Verify the element still exists in the DOM and is focusable
        if (
          document.body.contains(previousElement) &&
          typeof previousElement.focus === "function"
        ) {
          // Check if the element is not disabled and is visible
          const isDisabled =
            previousElement.hasAttribute("disabled") ||
            previousElement.getAttribute("aria-disabled") === "true";
          const style = window.getComputedStyle(previousElement);
          const isVisible =
            style.display !== "none" && style.visibility !== "hidden";

          if (!isDisabled && isVisible) {
            previousElement.focus();
          }
        }
      });

      // Clear the stored reference after restoration attempt
      previouslyFocusedElementRef.current = null;
    }
  }, [isOpen]);

  // Escape key handler will be implemented in subtask 1.5
};

export default useFocusTrap;
