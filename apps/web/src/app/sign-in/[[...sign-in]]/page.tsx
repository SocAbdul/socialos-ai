import { SignIn } from "@clerk/nextjs";

import { AuthDisabled } from "@/components/auth-disabled";

export default function SignInPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <AuthDisabled />;
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f8f8fa] p-6">
      <SignIn />
    </main>
  );
}
