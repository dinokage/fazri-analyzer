'use client';

import { useState, useEffect } from 'react';
import { AlertDetail } from '@/components/alerts';
import { AlertNotificationListener } from '@/components/alert-notification-listener';
import { useSession } from '@/lib/auth-client';

export default function AlertDetailPageContent({ alertId }: { alertId: string }) {
  const { data: session } = useSession();
  const [staffId, setStaffId] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!session?.user?.email) return;

    async function fetchStaffId() {
      try {
        const tokenRes = await fetch(
          `${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/api/auth/token`,
          { credentials: 'include' }
        );
        const tokenData = tokenRes.ok ? await tokenRes.json() : null;
        const token = tokenData?.token;
        if (!token) { setError(true); return; }

        const baseUrl = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL || 'http://localhost:8000';
        const res = await fetch(
          `${baseUrl}/api/v1/staff/by-email/${encodeURIComponent(session!.user.email!)}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!res.ok) { setError(true); return; }
        const data = await res.json();
        setStaffId(data.id || null);
        if (!data.id) setError(true);
      } catch {
        setError(true);
      }
    }

    fetchStaffId();
  }, [session?.user?.email]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Staff Profile Not Found</h2>
          <p className="text-gray-400">
            Your account is not linked to a staff profile. Please contact an administrator.
          </p>
        </div>
      </div>
    );
  }

  if (!staffId) return null;

  return (
    <>
      <AlertNotificationListener enabled pollInterval={30000} />
      <AlertDetail alertId={alertId} staffId={staffId} />
    </>
  );
}
