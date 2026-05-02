import { act, render, screen } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.mock("next/dynamic", () => ({
  default: () =>
    function ForceGraphMock(props: { width: number; height: number }) {
      return (
        <div
          data-height={props.height}
          data-testid="force-graph"
          data-width={props.width}
        />
      );
    }
}));

import { EvidenceGraphVisual } from "../components/evidence-graph-visual";

class ResizeObserverMock {
  static instances: ResizeObserverMock[] = [];

  callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    ResizeObserverMock.instances.push(this);
  }

  observe = vi.fn();
  disconnect = vi.fn();

  trigger(width: number) {
    this.callback(
      [
        {
          contentRect: { width }
        } as ResizeObserverEntry
      ],
      this as unknown as ResizeObserver
    );
  }
}

const originalResizeObserver = globalThis.ResizeObserver;

afterEach(() => {
  ResizeObserverMock.instances = [];
  globalThis.ResizeObserver = originalResizeObserver;
});

it("uses a taller canvas and responds to container resizes", () => {
  globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

  render(
    <EvidenceGraphVisual
      edges={[
        {
          id: "edge-1",
          source: "provider-1",
          target: "org-1",
          relationship: "managed_by",
          evidence: "Provider is managed by the organization.",
          sourceType: "Palantir AIP"
        }
      ]}
      nodes={[
        { id: "provider-1", label: "Provider", type: "provider", source: "Local Rule" },
        { id: "org-1", label: "Apex Review Group", type: "organization", source: "Palantir AIP" }
      ]}
    />
  );

  expect(screen.getByTestId("force-graph")).toHaveAttribute("data-height", "420");
  expect(ResizeObserverMock.instances).toHaveLength(1);

  act(() => {
    ResizeObserverMock.instances[0].trigger(860);
  });

  expect(screen.getByTestId("force-graph")).toHaveAttribute("data-width", "860");
});
