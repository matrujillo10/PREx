"use client";

/**
 * CopilotKitProviderShell — client-side wrapper around CopilotKitProvider.
 *
 * Why this lives in its own file: the provider config can carry non-plain
 * values (component refs, etc.) that can't be serialized across the
 * server→client boundary if registered directly inside the root
 * server-component layout. Wrapping the provider in this client component
 * keeps that wiring client-side, and the server layout just renders
 * <CopilotKitProviderShell>{children}</…>.
 *
 */

import { CopilotKitProvider } from "@copilotkit/react-core/v2";

export function CopilotKitProviderShell({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <CopilotKitProvider
      // Point directly at the BFF in dev to bypass the Next.js rewrite,
      // which buffers SSE under turbopack and blocks streamed tool-call
      // events until the connection closes. NEXT_PUBLIC_BFF_URL must be
      // set in apps/frontend/.env.local (e.g. http://localhost:4000).
      runtimeUrl={`${process.env.NEXT_PUBLIC_BFF_URL ?? ""}/api/copilotkit`}
      publicApiKey={process.env.NEXT_PUBLIC_COPILOT_CLOUD_PUBLIC_API_KEY}
      openGenerativeUI={{}}
    >
      {children}
    </CopilotKitProvider>
  );
}
