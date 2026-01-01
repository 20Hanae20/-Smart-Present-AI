"use client";

import RoleGuard from '@/components/auth/RoleGuard';
import NTIC2Chat from '@/components/assistant/NTIC2Chat';

export const dynamic = 'force-dynamic';

export default function AssistantPage() {
  return (
    <RoleGuard allow={['admin', 'trainer', 'student']}>
      <div className="h-[calc(100vh-12rem)]">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white">Assistant IA NTIC2</h1>
          <p className="text-white/60 mt-2">Posez vos questions sur l'ISTA, les cours, les stages et plus encore</p>
        </div>
        <NTIC2Chat />
      </div>
    </RoleGuard>
  );
}
