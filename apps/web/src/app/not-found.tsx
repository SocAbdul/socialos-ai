import { Compass } from "lucide-react";

import { DashboardLink, FullPageState } from "@/components/full-page-state";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <FullPageState
      badge="404"
      title="This page is not in your workspace."
      description="The link may be outdated, or the resource may belong to another workspace. Head back to the dashboard to continue your publishing flow."
      icon={Compass}
      primaryAction={<DashboardLink />}
      secondaryAction={
        <Button asChild variant="outline">
          <a href="mailto:support@socialos.ai">Contact support</a>
        </Button>
      }
    />
  );
}
