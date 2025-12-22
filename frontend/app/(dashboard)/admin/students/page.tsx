'use client';

export const dynamic = 'force-dynamic';
import RoleGuard from '@/components/auth/RoleGuard';
import nextDynamic from 'next/dynamic';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import AdvancedFilters from '@/components/ui/AdvancedFilters';
import OnboardingTour from '@/components/OnboardingTour';
import { ColumnDef } from '@tanstack/react-table';
import { useQueryClient, useMutation, useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useMemo, useState } from 'react';
import {
  Edit2,
  Trash2,
  Download,
  RefreshCw,
  Plus,
  Sparkles,
  GraduationCap,
  FileSpreadsheet,
} from 'lucide-react';
import ErrorBanner from '@/components/ui/ErrorBanner';
import EmptyState from '@/components/ui/EmptyState';
import { TableSkeleton } from '@/components/ui/skeleton';
import { getApiBase } from '@/lib/config';
import { useEffect } from 'react';
import { getWebSocketManager } from '@/lib/websocket';
import { exportCSV, exportExcelLike } from '@/lib/export';
import { useSearchParams, useRouter } from 'next/navigation';

const DataTableWithBulk = nextDynamic(() => import('@/components/table/DataTableWithBulk'), {
  ssr: false,
  loading: () => <TableSkeleton />,
});

const StudentCreateEditModal = nextDynamic(
  () => import('@/components/modals/StudentCreateEditModal'),
  {
    ssr: false,
  },
);

type Student = {
  id: number;
  name: string;
  student_code: string;
  class_name?: string;
  facial_data_encoded?: boolean;
  pourcentage?: number;  // AI attendance score (0-100)
  justification?: string;  // AI explanation
};

export default function AdminStudentsPage() {
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [aiExplanation, setAiExplanation] = useState<{ student: string; score: number; text: string } | null>(null);
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const router = useRouter();

  const updateCachedLists = (updater: (items: Student[]) => Student[]) => {
    const queries = queryClient.getQueriesData<{ items: Student[]; total_pages: number }>({
      queryKey: ['admin-students'],
    });
    queries.forEach(([key, value]) => {
      if (!value) return;
      queryClient.setQueryData(key, {
        ...value,
        items: updater(value.items || []),
      });
    });
  };

  const apiBase = getApiBase();
  const authHeaders = useMemo(() => {
    if (typeof window === 'undefined') return {};
    const token = localStorage.getItem('spa_access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['admin-students', page, search, filters],
    queryFn: async () => {
      const res = await axios.get(`${apiBase}/api/admin/students`, {
        params: { page: page + 1, page_size: 10, search, ...filters },
        headers: authHeaders,
      });
      return res.data as { items: Student[]; total_pages: number };
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Hydrate state from URL on mount
  useEffect(() => {
    const urlPage = Number(searchParams.get('page') || 1) - 1; // Convert to 0-indexed
    const urlSearch = searchParams.get('q') || '';
    const urlFilters = searchParams.get('filters');
    if (urlPage !== page) setPage(urlPage);
    if (urlSearch !== search) setSearch(urlSearch);
    if (urlFilters) {
      try {
        const parsed = JSON.parse(urlFilters);
        setFilters(parsed);
      } catch {
        /* ignore invalid */
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync state to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (page > 0) params.set('page', String(page + 1)); // Convert to 1-indexed for URL
    if (search) params.set('q', search);
    if (Object.keys(filters).length > 0) params.set('filters', JSON.stringify(filters));
    const qs = params.toString();
    router.replace(`/admin/students${qs ? `?${qs}` : ''}`);
  }, [page, search, filters, router]);

  useEffect(() => {
    const ws = getWebSocketManager();
    ws.connect();
    const unsubCreate = ws.subscribe('student_created', () => {
      queryClient.invalidateQueries({ queryKey: ['admin-students'] });
    });
    const unsubUpdate = ws.subscribe('student_updated', () => {
      queryClient.invalidateQueries({ queryKey: ['admin-students'] });
    });
    const unsubDelete = ws.subscribe('student_deleted', () => {
      queryClient.invalidateQueries({ queryKey: ['admin-students'] });
    });
    return () => {
      unsubCreate();
      unsubUpdate();
      unsubDelete();
    };
  }, [queryClient]);

  const createMutation = useMutation({
    mutationFn: (newStudent: any) =>
      axios.post(`${apiBase}/api/admin/students`, newStudent, { headers: authHeaders }),
    onMutate: async (newStudent) => {
      await queryClient.cancelQueries({ queryKey: ['admin-students'] });
      updateCachedLists((items) => [
        {
          id: Date.now(),
          name: newStudent.name,
          student_code: newStudent.student_code,
          class_name: newStudent.class_name,
          facial_data_encoded: false,
        },
        ...items,
      ]);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-students'] });
      setIsModalOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      axios.delete(`${apiBase}/api/admin/students/${id}`, { headers: authHeaders }),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['admin-students'] });
      updateCachedLists((items) => items.filter((s) => s.id !== id));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-students'] });
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) =>
      Promise.all(
        ids.map((id) =>
          axios.delete(`${apiBase}/api/admin/students/${id}`, { headers: authHeaders }),
        ),
      ),
    onMutate: async (ids) => {
      await queryClient.cancelQueries({ queryKey: ['admin-students'] });
      updateCachedLists((items) => items.filter((s) => !ids.includes(s.id)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-students'] });
    },
  });

  const bulkExportMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      const selectedStudents = data?.items.filter((s: Student) => ids.includes(s.id)) || [];
      const rows = [
        ['ID', 'Nom', 'Code', 'Classe', 'Visage Enrôlé'],
        ...selectedStudents.map((s: Student) => [
          s.id,
          s.name,
          s.student_code,
          s.class_name || '',
          s.facial_data_encoded ? 'Oui' : 'Non',
        ]),
      ];
      exportCSV(rows, `etudiants_export_${Date.now()}`);
      exportExcelLike(rows, `etudiants_export_${Date.now()}`);
    },
  });

  const columns: ColumnDef<any>[] = [
    { header: 'Nom', accessorKey: 'name' },
    { header: 'Code', accessorKey: 'student_code' },
    { header: 'Classe', accessorKey: 'class_name' },
    {
      header: 'Visage',
      cell: ({ row }) => (
        <span
          className={`rounded px-2 py-0.5 text-xs ${row.original.facial_data_encoded ? 'bg-emerald-700/40 text-emerald-300' : 'bg-zinc-700/40 text-zinc-300'}`}
        >
          {row.original.facial_data_encoded ? 'Enrôlé' : 'Manquant'}
        </span>
      ),
    },
    {
      header: 'Score IA',
      cell: ({ row }) => {
        const score = row.original.pourcentage;
        const justification = row.original.justification;
        
        if (score === null || score === undefined) {
          return <span className="text-xs text-zinc-500">—</span>;
        }
        
        return (
          <div className="flex items-center gap-2">
            <span
              className={`font-semibold ${
                score >= 80 ? 'text-emerald-400' :
                score >= 60 ? 'text-amber-400' :
                'text-red-400'
              }`}
            >
              {score}
            </span>
            {justification && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setAiExplanation({
                    student: row.original.name,
                    score: score,
                    text: justification
                  });
                }}
                className="rounded p-1 hover:bg-purple-900/30 text-purple-400 hover:text-purple-300 transition-colors"
                title="Voir l'explication IA"
                type="button"
              >
                <Sparkles className="h-3 w-3" />
              </button>
            )}
          </div>
        );
      },
    },
    {
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex gap-1">
          <button
            className="rounded p-1 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
            aria-label="Modifier"
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            onClick={() => deleteMutation.mutate(row.original.id)}
            className="rounded p-1 hover:bg-red-900/30 text-zinc-400 hover:text-red-400"
            aria-label="Supprimer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const advancedFilters = [
    {
      name: 'facial_status',
      type: 'select' as const,
      label: 'Statut facial',
      options: [
        { id: 'enrolled', label: 'Enrôlé' },
        { id: 'not_enrolled', label: 'Non enrôlé' },
      ],
    },
    {
      name: 'class_name',
      type: 'text' as const,
      label: 'Classe',
    },
    {
      name: 'tags',
      type: 'multiselect' as const,
      label: 'Statuts/Tags',
      options: [
        { id: 'active', label: 'Actif' },
        { id: 'inactive', label: 'Inactif' },
        { id: 'alert', label: 'Alerte' },
      ],
    },
  ];

  return (
    <RoleGuard allow={['admin']}>
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Breadcrumbs items={[{ label: 'Admin', href: '/admin' }, { label: 'Étudiants' }]} />

        <div className="relative overflow-hidden rounded-2xl border border-amber-500/15 bg-gradient-to-br from-amber-500/10 via-zinc-950 to-black p-6">
          <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_20%_20%,rgba(251,191,36,0.2),transparent_35%),radial-gradient(circle_at_80%_0%,rgba(255,255,255,0.08),transparent_30%)]" />
          <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <p className="inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.2em] text-amber-200">
                <Sparkles className="h-4 w-4" /> Cohortes
              </p>
              <h1 className="text-3xl font-semibold text-white">Étudiants</h1>
              <p className="max-w-2xl text-sm text-white/70">
                Filtrez les cohortes, suivez le statut facial et exportez en CSV en un clic.
              </p>
            </div>
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/80 shadow-lg">
              <GraduationCap className="h-5 w-5 text-amber-300" />
              <div>
                <p className="font-semibold text-white">{data?.items?.length ?? 0} étudiants</p>
                <p className="text-xs text-white/70">Page {page}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              label: 'Total page',
              value: data?.items?.length ?? 0,
              tone: 'text-amber-200',
              bg: 'bg-amber-500/15',
            },
            {
              label: 'Visage enrôlé',
              value: data?.items?.filter((s: Student) => s.facial_data_encoded)?.length ?? 0,
              tone: 'text-emerald-200',
              bg: 'bg-emerald-500/15',
            },
            {
              label: 'Manquants',
              value: Math.max(
                (data?.items?.length ?? 0) -
                  (data?.items?.filter((s: Student) => s.facial_data_encoded)?.length ?? 0),
                0,
              ),
              tone: 'text-red-200',
              bg: 'bg-red-500/15',
            },
          ].map((card) => (
            <div
              key={card.label}
              className={`rounded-xl border border-white/10 ${card.bg} px-4 py-3 shadow-sm`}
            >
              <p className="text-xs uppercase tracking-[0.2em] text-white/60">{card.label}</p>
              <p className={`text-2xl font-semibold ${card.tone}`}>{card.value}</p>
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-4 shadow-sm space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex flex-1 items-center gap-2 rounded-lg border border-white/10 bg-zinc-950 px-3 py-2">
              <input
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Rechercher par nom, code ou classe"
                className="w-full bg-transparent text-sm text-white placeholder:text-zinc-600 focus:outline-none"
              />
            </div>
            <AdvancedFilters
              filters={advancedFilters}
              onApply={(f) => {
                setFilters(f);
                setPage(1);
              }}
              onReset={() => {
                setFilters({});
                setPage(1);
              }}
              presetKey="admin-students"
              data-tour-id="students-filters"
            />
            <div className="flex gap-2">
              <button
                onClick={() => queryClient.invalidateQueries({ queryKey: ['admin-students'] })}
                className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-white hover:bg-white/5"
              >
                <RefreshCw className="h-4 w-4" /> Rafraîchir
              </button>
              <button
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
              >
                <Plus className="h-4 w-4" /> Créer
              </button>
            </div>
          </div>
          <DataTableWithBulk
            data={data?.items ?? []}
            columns={columns}
            currentPage={page}
            totalPages={data?.total_pages || 1}
            onPageChange={setPage}
            isLoading={isLoading}
            onBulkDelete={(ids) => bulkDeleteMutation.mutate(ids)}
            onBulkExport={(ids) => bulkExportMutation.mutate(ids)}
            getRowId={(row) => row.id}
          />
        </div>

        {/* Onboarding tour */}
        <OnboardingTour
          tourId="students"
          steps={[
            {
              target: "[data-tour-id='students-filters']",
              title: 'Filtres avancés',
              content: 'Affinez votre recherche par statut facial et classe.',
              placement: 'bottom',
            },
            {
              target: "button[aria-label='Supprimer'], button:has(svg.lucide-refresh-cw)",
              title: 'Rafraîchir en temps réel',
              content:
                "Les mises à jour WebSocket s'appliquent automatiquement; forcez ici si besoin.",
              placement: 'right',
            },
            {
              target: 'button:has(svg.lucide-plus)',
              title: 'Créer un étudiant',
              content: 'Ajoutez de nouveaux étudiants et gérez leur statut facial.',
              placement: 'right',
            },
          ]}
          autoStart
        />

        <StudentCreateEditModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          isLoading={createMutation.isPending}
        />

        {/* AI Explanation Modal */}
        {aiExplanation && (
          <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
            onClick={() => setAiExplanation(null)}
          >
            <div 
              className="relative max-w-2xl w-full mx-4 bg-gradient-to-br from-purple-950/90 via-zinc-900/95 to-black border border-purple-500/30 rounded-2xl shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="border-b border-purple-500/20 p-6">
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-purple-500/20 p-3">
                    <Sparkles className="h-6 w-6 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">
                      Explication IA - {aiExplanation.student}
                    </h3>
                    <p className="text-sm text-purple-300">
                      Score d'assiduité: {aiExplanation.score}/100
                    </p>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="p-6">
                <div className="rounded-xl bg-white/5 border border-white/10 p-6">
                  <p className="text-zinc-200 leading-relaxed whitespace-pre-wrap">
                    {aiExplanation.text}
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="border-t border-purple-500/20 p-4 flex justify-end">
                <button
                  onClick={() => setAiExplanation(null)}
                  className="px-6 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </RoleGuard>
  );
}
