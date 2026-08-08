"use client";

import { useFormStatus } from "react-dom";
import { LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function SubmitButton({
  children,
  className,
  disabled = false,
  pendingLabel = "Working...",
  variant,
  name,
  value,
}: {
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
  pendingLabel?: string;
  variant?: "default" | "outline" | "ghost";
  name?: string;
  value?: string;
}) {
  const { pending } = useFormStatus();

  return (
    <Button
      aria-disabled={pending || disabled}
      className={cn("min-h-11", className)}
      disabled={pending || disabled}
      name={name}
      value={value}
      variant={variant}
    >
      {pending ? (
        <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
      ) : null}
      <span aria-live="polite">{pending ? pendingLabel : children}</span>
    </Button>
  );
}
