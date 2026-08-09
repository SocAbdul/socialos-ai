"use client";

import { ImagePlus, Sparkles, X } from "lucide-react";
import Image from "next/image";
import { useActionState, useEffect, useId, useMemo, useRef, useState } from "react";

import { createWalkthroughPublicationAction, type WalkthroughActionState } from "@/app/actions";
import { SubmitButton } from "@/components/submit-button";
import {
  type WalkthroughField,
  type WalkthroughFieldErrors,
  validateWalkthrough,
  walkthroughLimits,
} from "@/lib/walkthrough-validation";

const initialState: WalkthroughActionState = { errors: {}, message: null };

export type ComposerPlatform = {
  provider: string;
  platform: string;
  displayName: string;
  supportsText: boolean;
  supportsSingleImage: boolean;
};

export function WalkthroughForm({ platforms, workspaceId }: { platforms: ComposerPlatform[]; workspaceId: string }) {
  const [state, formAction] = useActionState(createWalkthroughPublicationAction, initialState);
  const [clientErrors, setClientErrors] = useState<WalkthroughFieldErrors>({});
  const [file, setFile] = useState<File | null>(null);
  const reactId = useId();
  const submissionId = `${workspaceId}:${reactId}`;
  const preview = useMemo(() => file ? URL.createObjectURL(file) : null, [file]);
  const formRef = useRef<HTMLFormElement>(null);
  const errors = Object.keys(clientErrors).length ? clientErrors : state.errors;

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [preview]);
  useEffect(() => focusFirstInvalid(formRef.current, errors), [errors]);

  return (
    <form action={formAction} className="mt-6 grid gap-6" noValidate ref={formRef}
      onSubmit={(event) => {
        const data = new FormData(event.currentTarget);
        const submitter = event.nativeEvent.submitter;
        if (submitter instanceof HTMLButtonElement && submitter.value) data.set("delivery", submitter.value);
        const result = validateWalkthrough(data);
        if (result.data) { setClientErrors({}); return; }
        event.preventDefault(); setClientErrors(result.errors);
      }}>
      <input name="workspaceId" type="hidden" value={workspaceId} />
      <input name="submissionId" type="hidden" value={submissionId} />
      {Object.keys(errors).length || state.message ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          <p className="font-semibold">Check the highlighted fields.</p>{state.message ? <p>{state.message}</p> : null}
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-2">
        <Field error={errors.brandName} label="Brand Profile" maxLength={walkthroughLimits.brandName} name="brandName" placeholder="Kinetic Mobiles" />
        <Field error={errors.campaignName} label="Campaign" maxLength={walkthroughLimits.campaignName} name="campaignName" placeholder="Same-day repair launch" />
        <Field error={errors.voice} label="Brand voice" maxLength={walkthroughLimits.profileText} multiline name="voice" placeholder="Helpful, precise and confident." />
        <Field error={errors.audience} label="Audience" maxLength={walkthroughLimits.profileText} multiline name="audience" placeholder="Local professionals and families." />
      </div>
      <Field error={errors.contentBody} label="Base content" maxLength={walkthroughLimits.contentBody} multiline name="contentBody" placeholder="Describe the announcement you want to publish." />
      <fieldset className="grid gap-3 rounded-2xl border border-zinc-200 p-4">
        <legend className="px-2 text-sm font-semibold">Publish to</legend>
        <div className="flex flex-wrap gap-4">
          {platforms.map((platform) => <PlatformChoice disabled={!platform.supportsSingleImage} key={`${platform.provider}:${platform.platform}`} label={platform.displayName} value={platform.platform} />)}
        </div>
        {platforms.length === 0 ? <p className="text-xs text-amber-700">Connect an implemented account with single-image support to publish.</p> : null}
        {errors.platforms ? <p className="text-xs font-medium text-red-600" id="platforms-error">{errors.platforms}</p> : null}
      </fieldset>
      <div className="grid gap-4 md:grid-cols-2">
        {platforms.map((platform) => <Field error={errors[`caption:${platform.platform}`]} key={`${platform.provider}:${platform.platform}`} label={`${platform.displayName} caption`} maxLength={walkthroughLimits.caption} multiline name={`caption:${platform.platform}`} placeholder="Leave empty to use the platform adaptation." />)}
      </div>
      <div className="grid gap-2 text-sm font-semibold text-zinc-700">
        <label className="flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-zinc-300 bg-zinc-50 p-5 text-center focus-within:ring-2 focus-within:ring-violet-500"
          onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setFile(event.dataTransfer.files[0] ?? null); }}>
          <ImagePlus className="mb-2 size-6 text-violet-600" /><span>Drop a JPEG or PNG here, or choose a file</span><span className="mt-1 text-xs font-normal text-zinc-500">Maximum 15 MB</span>
          <input accept="image/jpeg,image/png" className="sr-only" name="mediaFile" onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
        </label>
        {errors.mediaFile ? <p className="text-xs font-medium text-red-600" id="mediaFile-error">{errors.mediaFile}</p> : null}
        {preview ? <div className="relative w-fit"><Image alt="Selected media preview" className="max-h-72 rounded-xl border object-contain" height={720} src={preview} unoptimized width={720} /><button aria-label="Remove selected image" className="absolute right-2 top-2 grid size-11 place-items-center rounded-full bg-white shadow" onClick={() => { setFile(null); const input=formRef.current?.elements.namedItem("mediaFile"); if(input instanceof HTMLInputElement) input.value=""; }} type="button"><X className="size-4" /></button></div> : null}
      </div>
      {preview ? <div className="grid gap-4 md:grid-cols-2">{platforms.map((platform) => <Preview caption={`Your ${platform.displayName} caption or local adaptation`} image={preview} key={platform.platform} title={`${platform.displayName} preview`} />)}</div> : null}
      <label className="flex items-start gap-3 rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-600"><input className="mt-1" name="simulateRetryableError" type="checkbox" /><span>Simulate one retryable failure in local development only.</span></label>
      <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 text-sm text-violet-950"><p className="font-semibold">Final confirmation</p><p>One independent publication will be created for every selected platform. A failure on one platform will not remove a successful result on another.</p></div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <SubmitButton className="w-full sm:w-fit" disabled={!submissionId} name="delivery" value="now" pendingLabel="Uploading and publishing..."><Sparkles className="size-4" />Publish now</SubmitButton>
        <SubmitButton className="w-full sm:w-fit" disabled={!submissionId} name="delivery" value="schedule" pendingLabel="Uploading and scheduling..." variant="outline">Schedule in 15 minutes</SubmitButton>
      </div>
    </form>
  );
}

function PlatformChoice({ disabled, value, label }: { disabled: boolean; value: string; label: string }) { return <label className={`flex min-h-11 items-center gap-2 rounded-xl border border-zinc-200 px-4 ${disabled ? "cursor-not-allowed bg-zinc-100 text-zinc-400" : ""}`}><input disabled={disabled} name="platform" type="checkbox" value={value} /><span>{label}{disabled ? " · Not connected" : ""}</span></label>; }
function Preview({ title, image, caption }: { title: string; image: string; caption: string }) { return <article className="overflow-hidden rounded-2xl border border-zinc-200 bg-white"><p className="p-3 text-sm font-semibold">{title}</p><Image alt="" className="aspect-square w-full object-cover" height={720} src={image} unoptimized width={720} /><p className="p-3 text-sm text-zinc-600">{caption}</p></article>; }
function Field({ error, label, maxLength, multiline=false, name, placeholder }: { error?: string; label: string; maxLength: number; multiline?: boolean; name: WalkthroughField; placeholder: string }) { const props={"aria-describedby":error?`${name}-error`:undefined,"aria-invalid":Boolean(error),className:`rounded-xl border bg-white px-3 text-sm font-normal outline-none ring-violet-500 focus:ring-2 ${multiline?"min-h-28 py-2":"h-11"} ${error?"border-red-400":"border-zinc-200"}`,id:name,maxLength,name,placeholder}; return <div className="grid gap-2 text-sm font-semibold text-zinc-700"><label htmlFor={name}>{label}</label>{multiline?<textarea {...props}/>:<input {...props}/>} {error?<p className="text-xs font-medium text-red-600" id={`${name}-error`}>{error}</p>:null}</div>; }
function focusFirstInvalid(form: HTMLFormElement | null, errors: WalkthroughFieldErrors) { if(!form)return; const first=Object.keys(errors)[0] as WalkthroughField|undefined; const element=first?form.elements.namedItem(first):null; if(element instanceof HTMLElement)element.focus(); }
