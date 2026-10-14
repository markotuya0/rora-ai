"use client";

import { useEffect } from "react";

export interface Shortcut {
  key: string;
  /** Requires ⌘ (mac) or Ctrl (other). */
  mod?: boolean;
  handler: (event: KeyboardEvent) => void;
}

function isEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

/**
 * Global shortcuts. Plain keys are ignored while typing in a field so "1" or "/"
 * can still be typed into the prompt; modifier shortcuts work everywhere.
 */
export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const mod = event.metaKey || event.ctrlKey;
      if (!mod && isEditable(event.target)) return;
      for (const s of shortcuts) {
        if (event.key !== s.key) continue;
        if ((s.mod ?? false) !== mod) continue;
        event.preventDefault();
        s.handler(event);
        return;
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [shortcuts]);
}
