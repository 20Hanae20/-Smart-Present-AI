'use client';

export const dynamic = 'force-dynamic';
import RoleGuard from '@/components/auth/RoleGuard';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { useQuery } from '@tanstack/react-query';
import { FileText, Download, Calendar, Clock, AlertCircle } from 'lucide-react';
import { useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { getApiBase } from '@/lib/config';

type PDFReport = {
  id: number;
  class: string;
  date: string;
  pdf_path: string;
  created_at: string;
};

export default function AdminReportsPage() {
  const [selectedClass, setSelectedClass] = useState<string>('all');

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['admin-pdf-reports'],
    queryFn: async () => {
      return apiClient<PDFReport[]>('/api/n8n/pdfs/recent?limit=50', { method: 'GET' });
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const filteredReports = selectedClass === 'all'
    ? reports
    : reports.filter((r) => r.class === selectedClass);

  const uniqueClasses = Array.from(new Set(reports.map((r) => r.class)));

  const handleDownload = async (report: PDFReport) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${getApiBase()}/api/n8n/pdfs/download/${report.id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Échec du téléchargement');
      }

      // Create blob from response
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      // Create download link
      const a = document.createElement('a');
      a.href = url;
      a.download = `absences_${report.class}_${report.date}.pdf`;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      alert('Erreur lors du téléchargement du PDF');
      console.error(error);
    }
  };

  return (
    <RoleGuard allow={['admin']}>
      <div className="mx-auto max-w-7xl p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Admin', href: '/admin' }, { label: 'Rapports PDF' }]} />

        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl border border-blue-500/15 bg-gradient-to-br from-blue-500/10 via-zinc-950 to-black p-6">
          <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.2),transparent_35%)]" />
          <div className="relative flex items-center gap-4">
            <div className="rounded-full bg-blue-500/20 p-3">
              <FileText className="h-8 w-8 text-blue-300" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-semibold text-white">Rapports PDF Quotidiens</h1>
              <p className="text-sm text-white/70 mt-1">
                Récapitulatifs d'absences générés automatiquement par N8N Workflow 5
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-white/60 uppercase tracking-wider">Total</p>
              <p className="text-3xl font-bold text-blue-300">{filteredReports.length}</p>
            </div>
          </div>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-3">
          <label className="text-sm text-zinc-400">Filtrer par classe:</label>
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="all">Toutes les classes</option>
            {uniqueClasses.map((cls) => (
              <option key={cls} value={cls}>
                {cls}
              </option>
            ))}
          </select>
        </div>

        {/* Reports List */}
        <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-zinc-400">
              <Clock className="h-8 w-8 mx-auto mb-2 animate-spin" />
              <p>Chargement des rapports...</p>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="p-12 text-center text-zinc-400">
              <AlertCircle className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium mb-1">Aucun rapport disponible</p>
              <p className="text-sm">
                Les PDFs seront générés automatiquement par N8N chaque jour à 23h59
              </p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {filteredReports.map((report) => (
                <div
                  key={report.id}
                  className="flex items-center justify-between p-4 hover:bg-white/5 transition"
                >
                  <div className="flex items-center gap-4">
                    <div className="rounded-lg bg-blue-500/20 p-3">
                      <FileText className="h-6 w-6 text-blue-300" />
                    </div>
                    <div>
                      <h3 className="font-medium text-white">
                        Absences - {report.class}
                      </h3>
                      <div className="flex items-center gap-3 mt-1 text-xs text-zinc-400">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(report.date).toLocaleDateString('fr-FR')}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Généré le {new Date(report.created_at).toLocaleString('fr-FR')}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownload(report)}
                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition"
                  >
                    <Download className="h-4 w-4" />
                    Télécharger
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info Card */}
        <div className="rounded-xl border border-purple-500/20 bg-purple-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-purple-300 mt-0.5" />
            <div className="text-sm text-purple-200">
              <p className="font-medium mb-1">À propos des rapports PDF</p>
              <ul className="space-y-1 text-purple-200/80">
                <li>• Générés automatiquement chaque jour à 23h59 par N8N Workflow 5</li>
                <li>• Contiennent la liste des absences du jour par classe</li>
                <li>• Incluent: nom étudiant, email parent, heures d'absence</li>
                <li>• Stockés dans: /app/storage/n8n_pdfs/</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </RoleGuard>
  );
}
