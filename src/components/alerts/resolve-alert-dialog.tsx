'use client';

import { useState } from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { apiClient } from '@/lib/api-client';
import type { Alert, ResolutionType } from '@/types/alert';
import { toast } from 'sonner';

interface ResolveAlertDialogProps {
  alert: Alert;
  staffId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onResolved?: () => void;
}

const RESOLUTION_TYPES: { value: ResolutionType; label: string; description: string }[] = [
  {
    value: 'resolved',
    label: 'Resolved',
    description: 'Issue has been addressed and resolved',
  },
  {
    value: 'false_alarm',
    label: 'False Alarm',
    description: 'Alert was triggered incorrectly',
  },
  {
    value: 'no_action_required',
    label: 'No Action Required',
    description: 'Reviewed but no intervention needed',
  },
];

export function ResolveAlertDialog({
  alert,
  staffId,
  open,
  onOpenChange,
  onResolved,
}: ResolveAlertDialogProps) {
  const [resolutionType, setResolutionType] = useState<ResolutionType>('resolved');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleResolve = async () => {
    if (!notes.trim()) {
      toast.error('Please provide resolution notes');
      return;
    }

    setLoading(true);
    try {
      await apiClient.resolveAlert(alert.id, {
        staff_id: staffId,
        resolution_type: resolutionType,
        resolution_notes: notes,
      });

      toast.success('Alert resolved successfully');
      onOpenChange(false);
      onResolved?.();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to resolve alert'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-gray-900 border-gray-800 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            Resolve Alert
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            Mark this alert as resolved with your notes.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label className="text-gray-300">Alert</Label>
            <p className="text-sm text-white font-medium">{alert.title}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="resolution-type" className="text-gray-300">
              Resolution Type
            </Label>
            <Select
              value={resolutionType}
              onValueChange={(v) => setResolutionType(v as ResolutionType)}
            >
              <SelectTrigger className="bg-gray-800 border-gray-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                {RESOLUTION_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-gray-400">{type.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="notes" className="text-gray-300">
              Resolution Notes
            </Label>
            <Input
              id="notes"
              placeholder="Describe how the alert was resolved..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="bg-gray-800 border-gray-700"
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleResolve}
            disabled={loading || !notes.trim()}
            className="bg-green-600 hover:bg-green-700"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Resolving...
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Resolve Alert
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
