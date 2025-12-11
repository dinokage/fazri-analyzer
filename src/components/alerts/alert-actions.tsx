'use client';

import { useState } from 'react';
import {
  Eye,
  Search,
  CheckCircle2,
  ArrowUpCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import type { Alert } from '@/types/alert';
import { ResolveAlertDialog } from './resolve-alert-dialog';
import { EscalateAlertDialog } from './escalate-alert-dialog';

interface AlertActionsProps {
  alert: Alert;
  staffId: string;
  onActionComplete?: () => void;
  compact?: boolean;
}

export function AlertActions({
  alert,
  staffId,
  onActionComplete,
  compact = false,
}: AlertActionsProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [showResolveDialog, setShowResolveDialog] = useState(false);
  const [showEscalateDialog, setShowEscalateDialog] = useState(false);

  const handleAcknowledge = async () => {
    setLoading('acknowledge');
    try {
      await apiClient.acknowledgeAlert(alert.id, staffId);
      toast.success('Alert acknowledged');
      onActionComplete?.();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to acknowledge alert'
      );
    } finally {
      setLoading(null);
    }
  };

  const handleStartInvestigation = async () => {
    setLoading('investigate');
    try {
      // Use note to mark investigation start
      await apiClient.addAlertNote(alert.id, staffId, 'Started investigation');
      toast.success('Investigation started');
      onActionComplete?.();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to start investigation'
      );
    } finally {
      setLoading(null);
    }
  };

  const isResolved = alert.status === 'resolved';
  const isAcknowledged = ['acknowledged', 'investigating', 'resolved'].includes(alert.status);
  const isInvestigating = alert.status === 'investigating';

  if (isResolved) {
    return (
      <div className="flex items-center gap-2 text-green-400">
        <CheckCircle2 className="h-4 w-4" />
        <span className="text-sm">Resolved</span>
      </div>
    );
  }

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {!isAcknowledged && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleAcknowledge}
            disabled={loading !== null}
          >
            {loading === 'acknowledge' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          className="text-green-400 border-green-800 hover:bg-green-900/30"
          onClick={() => setShowResolveDialog(true)}
          disabled={loading !== null}
        >
          <CheckCircle2 className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="text-orange-400 border-orange-800 hover:bg-orange-900/30"
          onClick={() => setShowEscalateDialog(true)}
          disabled={loading !== null}
        >
          <ArrowUpCircle className="h-4 w-4" />
        </Button>

        <ResolveAlertDialog
          alert={alert}
          staffId={staffId}
          open={showResolveDialog}
          onOpenChange={setShowResolveDialog}
          onResolved={onActionComplete}
        />
        <EscalateAlertDialog
          alert={alert}
          open={showEscalateDialog}
          onOpenChange={setShowEscalateDialog}
          onEscalated={onActionComplete}
        />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {!isAcknowledged && (
          <Button
            variant="outline"
            onClick={handleAcknowledge}
            disabled={loading !== null}
            className="flex-1 min-w-[140px]"
          >
            {loading === 'acknowledge' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Eye className="h-4 w-4 mr-2" />
            )}
            Acknowledge
          </Button>
        )}

        {isAcknowledged && !isInvestigating && (
          <Button
            variant="outline"
            onClick={handleStartInvestigation}
            disabled={loading !== null}
            className="flex-1 min-w-[140px]"
          >
            {loading === 'investigate' ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Search className="h-4 w-4 mr-2" />
            )}
            Start Investigation
          </Button>
        )}

        <Button
          variant="outline"
          className="flex-1 min-w-[140px] text-green-400 border-green-800 hover:bg-green-900/30"
          onClick={() => setShowResolveDialog(true)}
          disabled={loading !== null}
        >
          <CheckCircle2 className="h-4 w-4 mr-2" />
          Resolve
        </Button>

        <Button
          variant="outline"
          className="flex-1 min-w-[140px] text-orange-400 border-orange-800 hover:bg-orange-900/30"
          onClick={() => setShowEscalateDialog(true)}
          disabled={loading !== null}
        >
          <ArrowUpCircle className="h-4 w-4 mr-2" />
          Escalate
        </Button>
      </div>

      <ResolveAlertDialog
        alert={alert}
        staffId={staffId}
        open={showResolveDialog}
        onOpenChange={setShowResolveDialog}
        onResolved={onActionComplete}
      />
      <EscalateAlertDialog
        alert={alert}
        open={showEscalateDialog}
        onOpenChange={setShowEscalateDialog}
        onEscalated={onActionComplete}
      />
    </div>
  );
}
