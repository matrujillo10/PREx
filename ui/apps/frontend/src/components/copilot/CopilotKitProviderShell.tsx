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
      runtimeUrl="/api/copilotkit"
      publicApiKey={process.env.NEXT_PUBLIC_COPILOT_CLOUD_PUBLIC_API_KEY}
      openGenerativeUI={{}}
    >
      {children}
    </CopilotKitProvider>
  );
}
