"use client";

import { useFormStatus } from "react-dom";

import { Button } from "@/components/ui/button";

export function SubmitButton({
  children,
  className,
  variant,
}: {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "outline" | "ghost";
}) {
  const { pending } = useFormStatus();

  return (
    <Button className={className} disabled={pending} variant={variant}>
      {pending ? "Working..." : children}
    </Button>
  );
}
