"use client";

import { useFormStatus } from "react-dom";
import { LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SubmitButton({
  children,
  className,
  pendingLabel = "Working...",
  variant,
}: {
  children: React.ReactNode;
  className?: string;
  pendingLabel?: string;
  variant?: "default" | "outline" | "ghost";
}) {
  const { pending } = useFormStatus();

  return (
    <Button
      aria-disabled={pending}
      className={cn("min-h-11", className)}
      disabled={pending}
      variant={variant}
    >
      {pending ? (
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      ) : null}
      <span aria-live="polite">{pending ? pendingLabel : children}</span>
    </Button>
  );
}
