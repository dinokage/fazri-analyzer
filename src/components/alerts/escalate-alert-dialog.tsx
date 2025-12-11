'use client';

import { useState, useEffect } from 'react';
import { ArrowUpCircle, Loader2 } from 'lucide-react';
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
import type { Alert, StaffMember } from '@/types/alert';
import { toast } from 'sonner';

interface EscalateAlertDialogProps {
  alert: Alert;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEscalated?: () => void;
}

export function EscalateAlertDialog({
  alert,
  open,
  onOpenChange,
  onEscalated,
}: EscalateAlertDialogProps) {
  const [supervisors, setSupervisors] = useState<StaffMember[]>([]);
  const [selectedSupervisor, setSelectedSupervisor] = useState<string>('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStaff, setLoadingStaff] = useState(false);

  useEffect(() => {
    if (open) {
      loadSupervisors();
    }
  }, [open]);

  const loadSupervisors = async () => {
    setLoadingStaff(true);
    try {
      const response = await apiClient.getStaffList({
        role: 'supervisor',
        available_only: true,
      });
      setSupervisors(response.staff || []);
    } catch {
      toast.error('Failed to load supervisors');
    } finally {
      setLoadingStaff(false);
    }
  };

  const handleEscalate = async () => {
    if (!selectedSupervisor) {
      toast.error('Please select a supervisor');
      return;
    }
    if (!reason.trim()) {
      toast.error('Please provide an escalation reason');
      return;
    }

    setLoading(true);
    try {
      await apiClient.escalateAlert(alert.id, {
        escalate_to: selectedSupervisor,
        reason: reason,
      });

      toast.success('Alert escalated successfully');
      onOpenChange(false);
      onEscalated?.();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'Failed to escalate alert'
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
            <ArrowUpCircle className="h-5 w-5 text-orange-500" />
            Escalate Alert
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            Escalate this alert to a supervisor for further action.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label className="text-gray-300">Alert</Label>
            <p className="text-sm text-white font-medium">{alert.title}</p>
            <p className="text-xs text-gray-400">
              Current escalation count: {alert.escalation_count}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="supervisor" className="text-gray-300">
              Escalate To
            </Label>
            <Select
              value={selectedSupervisor}
              onValueChange={setSelectedSupervisor}
              disabled={loadingStaff}
            >
              <SelectTrigger className="bg-gray-800 border-gray-700">
                <SelectValue placeholder={loadingStaff ? 'Loading...' : 'Select supervisor'} />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                {supervisors.length === 0 ? (
                  <SelectItem value="none" disabled>
                    No supervisors available
                  </SelectItem>
                ) : (
                  supervisors.map((supervisor) => (
                    <SelectItem key={supervisor.id} value={supervisor.id}>
                      <div>
                        <div className="font-medium">{supervisor.name}</div>
                        <div className="text-xs text-gray-400">
                          Workload: {supervisor.current_workload}/{supervisor.max_workload}
                        </div>
                      </div>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="reason" className="text-gray-300">
              Escalation Reason
            </Label>
            <Input
              id="reason"
              placeholder="Why does this need supervisor attention?"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
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
            onClick={handleEscalate}
            disabled={loading || !selectedSupervisor || !reason.trim()}
            className="bg-orange-600 hover:bg-orange-700"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Escalating...
              </>
            ) : (
              <>
                <ArrowUpCircle className="h-4 w-4 mr-2" />
                Escalate Alert
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
