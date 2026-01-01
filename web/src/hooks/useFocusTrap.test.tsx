import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef, useState } from "react";
import { useFocusTrap, FOCUSABLE_SELECTOR } from "./useFocusTrap";

/**
 * Test component that wraps the useFocusTrap hook for testing
 */
function TestComponent({
  isActive,
  children,
}: {
  isActive: boolean;
  children: React.ReactNode;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(containerRef, isActive);

  return (
    <div ref={containerRef} data-testid="focus-trap-container">
      {children}
    </div>
  );
}

/**
 * Test component with toggle functionality
 */
function ToggleableTestComponent({ children }: { children: React.ReactNode }) {
  const [isActive, setIsActive] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(containerRef, isActive);

  return (
    <div>
      <button data-testid="trigger-button" onClick={() => setIsActive(true)}>
        Open
      </button>
      {isActive && (
        <div ref={containerRef} data-testid="focus-trap-container">
          {children}
          <button data-testid="close-button" onClick={() => setIsActive(false)}>
            Close
          </button>
        </div>
      )}
    </div>
  );
}

describe("FOCUSABLE_SELECTOR constant", () => {
  it("includes button:not([disabled])", () => {
    expect(FOCUSABLE_SELECTOR).toContain("button:not([disabled])");
  });

  it("includes input:not([disabled])", () => {
    expect(FOCUSABLE_SELECTOR).toContain("input:not([disabled])");
  });

  it("includes select:not([disabled])", () => {
    expect(FOCUSABLE_SELECTOR).toContain("select:not([disabled])");
  });

  it("includes textarea:not([disabled])", () => {
    expect(FOCUSABLE_SELECTOR).toContain("textarea:not([disabled])");
  });

  it("includes a[href]", () => {
    expect(FOCUSABLE_SELECTOR).toContain("a[href]");
  });

  it("includes [tabindex]:not([tabindex='-1'])", () => {
    expect(FOCUSABLE_SELECTOR).toContain("[tabindex]:not([tabindex='-1'])");
  });
});

describe("useFocusTrap hook", () => {
  beforeEach(() => {
    // Reset the DOM and focus state before each test
    document.body.innerHTML = "";
    cleanup();
  });

  afterEach(() => {
    cleanup();
  });

  describe("focus on activation", () => {
    it("moves focus to first focusable element when activated", async () => {
      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <button data-testid="second-button">Second</button>
        </TestComponent>
      );

      // Wait for requestAnimationFrame
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });
    });

    it("focuses container when no focusable elements exist", async () => {
      render(
        <TestComponent isActive={true}>
          <p>No focusable elements here</p>
        </TestComponent>
      );

      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("focus-trap-container")
        );
      });

      // Container should have tabindex="-1" for focus
      expect(screen.getByTestId("focus-trap-container")).toHaveAttribute(
        "tabindex",
        "-1"
      );
    });

    it("does not move focus when isActive is false", async () => {
      const externalButton = document.createElement("button");
      externalButton.setAttribute("data-testid", "external-button");
      document.body.appendChild(externalButton);
      externalButton.focus();

      render(
        <TestComponent isActive={false}>
          <button data-testid="first-button">First</button>
        </TestComponent>
      );

      // Focus should remain on external button
      expect(document.activeElement).toBe(externalButton);
    });
  });

  describe("Tab key cycling", () => {
    it("cycles forward through focusable elements with Tab", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <button data-testid="second-button">Second</button>
          <button data-testid="third-button">Third</button>
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });

      // Tab to second button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("second-button"));

      // Tab to third button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("third-button"));
    });

    it("wraps focus from last to first element with Tab", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <button data-testid="second-button">Second</button>
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });

      // Tab to second (last) button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("second-button"));

      // Tab should wrap to first button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("first-button"));
    });
  });

  describe("Shift+Tab key cycling", () => {
    it("cycles backward through focusable elements with Shift+Tab", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <button data-testid="second-button">Second</button>
          <button data-testid="third-button">Third</button>
        </TestComponent>
      );

      // Wait for initial focus and move to third button
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });

      // Move focus to the last button
      screen.getByTestId("third-button").focus();

      // Shift+Tab to second button
      await user.tab({ shift: true });
      expect(document.activeElement).toBe(screen.getByTestId("second-button"));

      // Shift+Tab to first button
      await user.tab({ shift: true });
      expect(document.activeElement).toBe(screen.getByTestId("first-button"));
    });

    it("wraps focus from first to last element with Shift+Tab", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <button data-testid="second-button">Second</button>
        </TestComponent>
      );

      // Wait for initial focus on first button
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });

      // Shift+Tab should wrap to last button
      await user.tab({ shift: true });
      expect(document.activeElement).toBe(screen.getByTestId("second-button"));
    });
  });

  describe("focus restoration on cleanup", () => {
    it("returns focus to previously focused element when deactivated", async () => {
      const user = userEvent.setup();

      render(<ToggleableTestComponent>
        <button data-testid="dialog-button">Dialog Button</button>
      </ToggleableTestComponent>);

      // Focus and click the trigger button
      const triggerButton = screen.getByTestId("trigger-button");
      triggerButton.focus();
      expect(document.activeElement).toBe(triggerButton);

      // Open the dialog
      await user.click(triggerButton);

      // Wait for focus to move to dialog content
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("dialog-button")
        );
      });

      // Close the dialog
      await user.click(screen.getByTestId("close-button"));

      // Focus should return to trigger button
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(triggerButton);
      });
    });
  });

  describe("disabled elements handling", () => {
    it("skips disabled buttons", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <button data-testid="disabled-button" disabled>
            Disabled
          </button>
          <button data-testid="third-button">Third</button>
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });

      // Tab should skip disabled and go to third button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("third-button"));
    });

    it("skips disabled inputs", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <input data-testid="first-input" type="text" />
          <input data-testid="disabled-input" type="text" disabled />
          <input data-testid="third-input" type="text" />
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(screen.getByTestId("first-input"));
      });

      // Tab should skip disabled and go to third input
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("third-input"));
    });
  });

  describe("various focusable elements", () => {
    it("handles all types of focusable elements", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="button">Button</button>
          <input data-testid="input" type="text" />
          <select data-testid="select">
            <option>Option</option>
          </select>
          <textarea data-testid="textarea"></textarea>
          <a data-testid="link" href="https://example.com">
            Link
          </a>
          <div data-testid="tabindex-div" tabIndex={0}>
            Focusable Div
          </div>
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(screen.getByTestId("button"));
      });

      // Tab through all elements
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("input"));

      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("select"));

      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("textarea"));

      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("link"));

      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("tabindex-div"));

      // Wrap back to button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("button"));
    });

    it("excludes elements with tabindex=-1", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="first-button">First</button>
          <div data-testid="non-focusable-div" tabIndex={-1}>
            Not Focusable
          </div>
          <button data-testid="second-button">Second</button>
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("first-button")
        );
      });

      // Tab should skip tabIndex=-1 element and go to second button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("second-button"));
    });
  });

  describe("focus trap boundary", () => {
    it("prevents focus from leaving container when focus is outside", async () => {
      render(
        <div>
          <button data-testid="outside-button">Outside</button>
          <TestComponent isActive={true}>
            <button data-testid="inside-button">Inside</button>
          </TestComponent>
        </div>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(
          screen.getByTestId("inside-button")
        );
      });

      // Simulate Tab keydown when focus is somehow outside the container
      const outsideButton = screen.getByTestId("outside-button");
      outsideButton.focus();

      // Dispatch Tab keydown event
      const tabEvent = new KeyboardEvent("keydown", {
        key: "Tab",
        bubbles: true,
        cancelable: true,
      });

      document.dispatchEvent(tabEvent);

      // Focus should return to first element inside
      expect(document.activeElement).toBe(screen.getByTestId("inside-button"));
    });
  });

  describe("single focusable element", () => {
    it("keeps focus on single element when tabbing", async () => {
      const user = userEvent.setup();

      render(
        <TestComponent isActive={true}>
          <button data-testid="only-button">Only Button</button>
        </TestComponent>
      );

      // Wait for initial focus
      await vi.waitFor(() => {
        expect(document.activeElement).toBe(screen.getByTestId("only-button"));
      });

      // Tab should keep focus on the same button
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId("only-button"));

      // Shift+Tab should also keep focus on the same button
      await user.tab({ shift: true });
      expect(document.activeElement).toBe(screen.getByTestId("only-button"));
    });
  });
});
