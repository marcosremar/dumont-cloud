import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "../index";

// Helper to render a test dropdown menu
function renderDropdownMenu(options = {}) {
  const {
    onItem1Click = vi.fn(),
    onItem2Click = vi.fn(),
    onItem3Click = vi.fn(),
    disabledItems = [],
  } = options;

  return render(
    <DropdownMenu>
      <DropdownMenuTrigger>Open Menu</DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuLabel>Actions</DropdownMenuLabel>
        <DropdownMenuItem
          onClick={onItem1Click}
          disabled={disabledItems.includes(1)}
        >
          Item 1
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={onItem2Click}
          disabled={disabledItems.includes(2)}
        >
          Item 2
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={onItem3Click}
          disabled={disabledItems.includes(3)}
        >
          Item 3
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

describe("DropdownMenu Keyboard Interactions", () => {
  describe("Opening and Closing", () => {
    it("should open dropdown when pressing Enter on trigger", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Focus the trigger and press Enter
      trigger.focus();
      fireEvent.keyDown(trigger, { key: "Enter" });

      // Dropdown should be open
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });
    });

    it("should open dropdown when pressing Space on trigger", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Focus the trigger and press Space
      trigger.focus();
      fireEvent.keyDown(trigger, { key: " " });

      // Dropdown should be open
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });
    });

    it("should close dropdown when pressing Escape", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Press Escape to close
      fireEvent.keyDown(document, { key: "Escape" });

      // Dropdown should be closed
      await waitFor(() => {
        expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
      });
    });

    it("should toggle dropdown state with Enter/Space on trigger", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open with Enter
      trigger.focus();
      fireEvent.keyDown(trigger, { key: "Enter" });
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Close with Enter
      fireEvent.keyDown(trigger, { key: "Enter" });
      await waitFor(() => {
        expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
      });
    });
  });

  describe("Focus Management", () => {
    it("should focus first item when dropdown opens", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);

      // First item should be focused
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });
    });

    it("should return focus to trigger when Escape closes dropdown", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Press Escape to close
      fireEvent.keyDown(document, { key: "Escape" });

      // Focus should return to trigger
      await waitFor(() => {
        expect(document.activeElement).toBe(trigger);
      });
    });

    it("should return focus to trigger when item is selected", async () => {
      const onItem1Click = vi.fn();
      renderDropdownMenu({ onItem1Click });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Click on an item
      const item1 = screen.getByRole("button", { name: "Item 1" });
      fireEvent.click(item1);

      // Focus should return to trigger
      await waitFor(() => {
        expect(document.activeElement).toBe(trigger);
      });
    });

    it("should return focus to trigger when clicking outside closes dropdown", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Click outside
      fireEvent.mouseDown(document.body);

      // Focus should return to trigger
      await waitFor(() => {
        expect(document.activeElement).toBe(trigger);
      });
    });
  });

  describe("Arrow Key Navigation", () => {
    it("should move focus to next item with ArrowDown", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });

      // Press ArrowDown
      fireEvent.keyDown(document, { key: "ArrowDown" });

      // Second item should be focused
      await waitFor(() => {
        const item2 = screen.getByRole("button", { name: "Item 2" });
        expect(document.activeElement).toBe(item2);
      });
    });

    it("should move focus to previous item with ArrowUp", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Navigate to second item first
      fireEvent.keyDown(document, { key: "ArrowDown" });
      await waitFor(() => {
        const item2 = screen.getByRole("button", { name: "Item 2" });
        expect(document.activeElement).toBe(item2);
      });

      // Press ArrowUp
      fireEvent.keyDown(document, { key: "ArrowUp" });

      // First item should be focused again
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });
    });

    it("should wrap to first item when pressing ArrowDown on last item", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Navigate to last item (Item 3)
      fireEvent.keyDown(document, { key: "ArrowDown" });
      fireEvent.keyDown(document, { key: "ArrowDown" });
      await waitFor(() => {
        const item3 = screen.getByRole("button", { name: "Item 3" });
        expect(document.activeElement).toBe(item3);
      });

      // Press ArrowDown again - should wrap to first item
      fireEvent.keyDown(document, { key: "ArrowDown" });
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });
    });

    it("should wrap to last item when pressing ArrowUp on first item", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });

      // Press ArrowUp on first item - should wrap to last item
      fireEvent.keyDown(document, { key: "ArrowUp" });
      await waitFor(() => {
        const item3 = screen.getByRole("button", { name: "Item 3" });
        expect(document.activeElement).toBe(item3);
      });
    });
  });

  describe("Item Selection with Enter/Space", () => {
    it("should trigger onClick when pressing Enter on focused item", async () => {
      const onItem1Click = vi.fn();
      renderDropdownMenu({ onItem1Click });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });

      // Press Enter on focused item
      const item1 = screen.getByRole("button", { name: "Item 1" });
      fireEvent.keyDown(item1, { key: "Enter" });

      // onClick should have been called
      expect(onItem1Click).toHaveBeenCalled();
    });

    it("should trigger onClick when pressing Space on focused item", async () => {
      const onItem2Click = vi.fn();
      renderDropdownMenu({ onItem2Click });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Navigate to second item
      fireEvent.keyDown(document, { key: "ArrowDown" });
      await waitFor(() => {
        const item2 = screen.getByRole("button", { name: "Item 2" });
        expect(document.activeElement).toBe(item2);
      });

      // Press Space on focused item
      const item2 = screen.getByRole("button", { name: "Item 2" });
      fireEvent.keyDown(item2, { key: " " });

      // onClick should have been called
      expect(onItem2Click).toHaveBeenCalled();
    });

    it("should close dropdown after selecting item with Enter", async () => {
      const onItem1Click = vi.fn();
      renderDropdownMenu({ onItem1Click });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Press Enter on focused item
      const item1 = screen.getByRole("button", { name: "Item 1" });
      fireEvent.keyDown(item1, { key: "Enter" });

      // Dropdown should be closed
      await waitFor(() => {
        expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
      });
    });

    it("should close dropdown after selecting item with Space", async () => {
      const onItem1Click = vi.fn();
      renderDropdownMenu({ onItem1Click });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Press Space on focused item
      const item1 = screen.getByRole("button", { name: "Item 1" });
      fireEvent.keyDown(item1, { key: " " });

      // Dropdown should be closed
      await waitFor(() => {
        expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
      });
    });
  });

  describe("Disabled Items", () => {
    it("should not register disabled items for keyboard navigation", async () => {
      renderDropdownMenu({ disabledItems: [2] });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        const item1 = screen.getByRole("button", { name: "Item 1" });
        expect(document.activeElement).toBe(item1);
      });

      // Press ArrowDown - should skip disabled Item 2 and go to Item 3
      fireEvent.keyDown(document, { key: "ArrowDown" });
      await waitFor(() => {
        const item3 = screen.getByRole("button", { name: "Item 3" });
        expect(document.activeElement).toBe(item3);
      });
    });

    it("should not trigger onClick on disabled items with Enter", async () => {
      const onItem1Click = vi.fn();
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open Menu</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={onItem1Click} disabled>
              Disabled Item
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const trigger = screen.getByRole("button", { name: "Open Menu" });
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText("Disabled Item")).toBeInTheDocument();
      });

      // Try to press Enter on disabled item
      const disabledItem = screen.getByRole("button", { name: "Disabled Item" });
      fireEvent.keyDown(disabledItem, { key: "Enter" });

      // onClick should NOT have been called
      expect(onItem1Click).not.toHaveBeenCalled();
    });

    it("should not trigger onClick on disabled items with Space", async () => {
      const onItem1Click = vi.fn();
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open Menu</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={onItem1Click} disabled>
              Disabled Item
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const trigger = screen.getByRole("button", { name: "Open Menu" });
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText("Disabled Item")).toBeInTheDocument();
      });

      // Try to press Space on disabled item
      const disabledItem = screen.getByRole("button", { name: "Disabled Item" });
      fireEvent.keyDown(disabledItem, { key: " " });

      // onClick should NOT have been called
      expect(onItem1Click).not.toHaveBeenCalled();
    });

    it("should focus first non-disabled item when dropdown opens", async () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open Menu</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem disabled>Disabled Item</DropdownMenuItem>
            <DropdownMenuItem>Enabled Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const trigger = screen.getByRole("button", { name: "Open Menu" });
      fireEvent.click(trigger);

      // First non-disabled item should be focused (since disabled items are not registered)
      await waitFor(() => {
        const enabledItem = screen.getByRole("button", { name: "Enabled Item" });
        expect(document.activeElement).toBe(enabledItem);
      });
    });
  });

  describe("Mouse Interactions (Regression Tests)", () => {
    it("should still open dropdown when clicking trigger", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });
    });

    it("should still close dropdown when clicking item", async () => {
      const onItem1Click = vi.fn();
      renderDropdownMenu({ onItem1Click });
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Click on item
      const item1 = screen.getByRole("button", { name: "Item 1" });
      fireEvent.click(item1);

      // Dropdown should close and onClick should be called
      expect(onItem1Click).toHaveBeenCalled();
      await waitFor(() => {
        expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
      });
    });

    it("should still close dropdown when clicking outside", async () => {
      renderDropdownMenu();
      const trigger = screen.getByRole("button", { name: "Open Menu" });

      // Open the dropdown
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText("Item 1")).toBeInTheDocument();
      });

      // Click outside
      fireEvent.mouseDown(document.body);

      await waitFor(() => {
        expect(screen.queryByText("Item 1")).not.toBeInTheDocument();
      });
    });
  });
});
