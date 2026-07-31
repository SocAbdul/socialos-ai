"use client";

import { Sparkles } from "lucide-react";
import {
  useActionState,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";

import {
  createWalkthroughPublicationAction,
  type WalkthroughActionState,
} from "@/app/actions";
import { SubmitButton } from "@/components/submit-button";
import {
  type WalkthroughField,
  type WalkthroughFieldErrors,
  validateWalkthrough,
  walkthroughLimits,
} from "@/lib/walkthrough-validation";

const initialState: WalkthroughActionState = { errors: {}, message: null };

export function WalkthroughForm({ workspaceId }: { workspaceId: string }) {
  const [state, formAction] = useActionState(
    createWalkthroughPublicationAction,
    initialState,
  );
  const [clientErrors, setClientErrors] = useState<WalkthroughFieldErrors>({});
  const hydrated = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  const formRef = useRef<HTMLFormElement>(null);
  const errors =
    Object.keys(clientErrors).length > 0 ? clientErrors : state.errors;

  useEffect(() => {
    focusFirstInvalid(formRef.current, errors);
  }, [errors]);

  return (
    <form
      action={formAction}
      className="mt-6 grid gap-5"
      noValidate
      onSubmit={(event) => {
        const result = validateWalkthrough(new FormData(event.currentTarget));
        if (result.data) {
          setClientErrors({});
          return;
        }
        event.preventDefault();
        setClientErrors(result.errors);
      }}
      ref={formRef}
    >
      <input name="workspaceId" type="hidden" value={workspaceId} />
      {Object.keys(errors).length > 0 || state.message ? (
        <div
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          role="alert"
          tabIndex={-1}
        >
          <p className="font-semibold">Check the highlighted fields.</p>
          {state.message ? <p className="mt-1">{state.message}</p> : null}
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-2">
        <Field
          error={errors.brandName}
          label="Brand Profile"
          maxLength={walkthroughLimits.brandName}
          name="brandName"
          placeholder="Kinetic Mobiles"
        />
        <Field
          error={errors.campaignName}
          label="Campaign"
          maxLength={walkthroughLimits.campaignName}
          name="campaignName"
          placeholder="Same-day repair launch"
        />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Field
          error={errors.voice}
          label="Brand voice"
          maxLength={walkthroughLimits.profileText}
          multiline
          name="voice"
          placeholder="Helpful, precise, practical and confident."
        />
        <Field
          error={errors.audience}
          label="Audience"
          maxLength={walkthroughLimits.profileText}
          multiline
          name="audience"
          placeholder="Local professionals and families who need reliable phone repairs."
        />
      </div>
      <Field
        error={errors.contentBody}
        label="Original content"
        maxLength={walkthroughLimits.contentBody}
        multiline
        name="contentBody"
        placeholder="Describe the announcement you want to publish."
      />
      <div className="grid gap-4 md:grid-cols-[.7fr_1.3fr]">
        <FieldShell error={errors.platform} label="Platform" name="platform">
          <select
            aria-describedby={errors.platform ? "platform-error" : undefined}
            aria-invalid={Boolean(errors.platform)}
            className={fieldClass(Boolean(errors.platform))}
            defaultValue="instagram"
            id="platform"
            name="platform"
          >
            <option value="instagram">Instagram local business</option>
            <option value="facebook">Facebook local page</option>
          </select>
        </FieldShell>
        <Field
          error={errors.mediaUrl}
          label="Media Asset URL"
          maxLength={walkthroughLimits.mediaUrl}
          name="mediaUrl"
          placeholder="https://media.example.com/image.jpg"
          type="url"
        />
      </div>
      <input name="contentType" type="hidden" value="image/jpeg" />
      <input
        name="checksumSha256"
        type="hidden"
        value="b4b9b02e6f09a9bd760f388b67351e2b1dd3bba6a63c10cf7e5f541d176ad39c"
      />
      <label className="flex items-start gap-3 rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-600">
        <input className="mt-1" name="simulateRetryableError" type="checkbox" />
        <span>
          Simulate one retryable failure. The next Retry will succeed.
        </span>
      </label>
      <SubmitButton
        className="w-full sm:w-fit"
        disabled={!hydrated}
        pendingLabel="Adapting and creating..."
      >
        <Sparkles className="size-4" />
        Adapt and create publication
      </SubmitButton>
    </form>
  );
}

function emptySubscribe() {
  return () => undefined;
}

function Field({
  error,
  label,
  maxLength,
  multiline = false,
  name,
  placeholder,
  type = "text",
}: {
  error?: string;
  label: string;
  maxLength: number;
  multiline?: boolean;
  name: WalkthroughField;
  placeholder: string;
  type?: "text" | "url";
}) {
  const attributes = {
    "aria-describedby": error ? `${name}-error` : undefined,
    "aria-invalid": Boolean(error),
    className: multiline
      ? `${fieldClass(Boolean(error))} min-h-28 py-2 leading-6`
      : fieldClass(Boolean(error)),
    id: name,
    maxLength,
    name,
    placeholder,
  };
  return (
    <FieldShell error={error} label={label} name={name}>
      {multiline ? (
        <textarea {...attributes} />
      ) : (
        <input {...attributes} type={type} />
      )}
    </FieldShell>
  );
}

function FieldShell({
  children,
  error,
  label,
  name,
}: {
  children: React.ReactNode;
  error?: string;
  label: string;
  name: WalkthroughField;
}) {
  return (
    <div className="grid gap-2 text-sm font-semibold text-zinc-700">
      <label htmlFor={name}>{label}</label>
      {children}
      {error ? (
        <p className="text-xs font-medium text-red-600" id={`${name}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

function fieldClass(invalid: boolean) {
  return `h-11 rounded-xl border bg-white px-3 text-sm font-normal text-zinc-800 outline-none ring-violet-500 transition focus:ring-2 ${
    invalid ? "border-red-400" : "border-zinc-200"
  }`;
}

function focusFirstInvalid(
  form: HTMLFormElement | null,
  errors: WalkthroughFieldErrors,
) {
  if (!form) return;
  const first = Object.keys(errors)[0] as WalkthroughField | undefined;
  const element = first ? form.elements.namedItem(first) : null;
  if (element instanceof HTMLElement) element.focus();
}
