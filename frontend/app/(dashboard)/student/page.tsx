'use client';
export const dynamic = 'force-dynamic';

import RoleGuard from '@/components/auth/RoleGuard';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Calendar,
  BookOpen,
  TrendingUp,
  AlertCircle,
  Clock,
  CheckCircle,
  XCircle,
  ChevronRight,
  Camera,
} from 'lucide-react';
import Link from 'next/link';
import { useMemo, useEffect } from 'react';
import OnboardingWalkthrough from '@/components/common/OnboardingWalkthrough';
import { getWebSocketManager } from '@/lib/websocket';
import OnboardingTour from '@/components/OnboardingTour';
import { apiClient } from '@/lib/api-client';

type StudentStats = {
  attendance_rate: number;
  total_classes?: number;
  total_sessions?: number;
  absent_count?: number;
  absences?: number;
  justified_absences?: number;
  next_session?: string;
  total_absence_hours?: number;
  total_late_minutes?: number;
  alert_level?: 'none' | 'warning' | 'critical' | 'failing';
  ai_score?: number;  // AI attendance score from N8N (0-100)
  ai_explanation?: string;  // AI explanation from N8N
};

type AttendanceRecord = {
  id: number;
  date: string;
  subject: string;
  status: 'present' | 'absent' | 'late' | 'excused';
  justified: boolean;
};

type UpcomingSession = {
  id: number;
  subject: string;
  date: string;
  time: string;
  classroom?: string;
  trainer_name?: string;
};

export default function StudentPage() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const ws = getWebSocketManager();
    ws.connect();
    const unsubStats = ws.subscribe('student_stats_updated', () => {
      queryClient.invalidateQueries({ queryKey: ['student-stats'] });
    });
    const unsubAttend = ws.subscribe('student_attendance_updated', () => {
      queryClient.invalidateQueries({ queryKey: ['student-attendance'] });
    });
    const unsubSessions = ws.subscribe('student_sessions_updated', () => {
      queryClient.invalidateQueries({ queryKey: ['student-upcoming-sessions'] });
    });
    return () => {
      unsubStats();
      unsubAttend();
      unsubSessions();
    };
  }, [queryClient]);

  const { data: stats } = useQuery({
    queryKey: ['student-stats'],
    queryFn: async () => {
      return apiClient<StudentStats>('/api/student/stats', { method: 'GET', useCache: false });
    },
  });

  const { data: attendance } = useQuery({
    queryKey: ['student-attendance'],
    queryFn: async () => {
      return apiClient<AttendanceRecord[]>('/api/student/attendance?limit=50', {
        method: 'GET',
        useCache: false,
      });
    },
  });

  const { data: upcomingSessions } = useQuery({
    queryKey: ['student-upcoming-sessions'],
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
    queryFn: async () => {
      return apiClient<UpcomingSession[]>('/api/student/upcoming-sessions?limit=10', {
        method: 'GET',
        useCache: false,
      });
    },
  });

  const statusCounts = useMemo(() => {
    if (!attendance) return { present: 0, absent: 0, late: 0, excused: 0 };
    return {
      present: attendance.filter((a) => a.status === 'present').length,
      absent: attendance.filter((a) => a.status === 'absent').length,
      late: attendance.filter((a) => a.status === 'late').length,
      excused: attendance.filter((a) => a.status === 'excused').length,
    };
  }, [attendance]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'present':
        return <CheckCircle className="h-4 w-4 text-emerald-400" />;
      case 'absent':
        return <XCircle className="h-4 w-4 text-red-400" />;
      case 'late':
        return <Clock className="h-4 w-4 text-amber-400" />;
      case 'excused':
        return <CheckCircle className="h-4 w-4 text-blue-400" />;
      default:
        return null;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'present':
        return 'Présent';
      case 'absent':
        return 'Absent';
      case 'late':
        return 'Retard';
      case 'excused':
        return 'Excusé';
      default:
        return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'present':
        return 'bg-emerald-600/20 text-emerald-300';
      case 'absent':
        return 'bg-red-600/20 text-red-300';
      case 'late':
        return 'bg-amber-600/20 text-amber-300';
      case 'excused':
        return 'bg-blue-600/20 text-blue-300';
      default:
        return 'bg-zinc-600/20 text-zinc-300';
    }
  };

  const cards = [
    {
      icon: TrendingUp,
      label: 'Taux de présence',
      value: `${(stats?.attendance_rate ?? 0).toFixed(1)}%`,
      color: 'bg-emerald-600/20 text-emerald-300',
    },
    {
      icon: BookOpen,
      label: 'Classes',
      value: stats?.total_classes ?? stats?.total_sessions ?? 0,
      color: 'bg-blue-600/20 text-blue-300',
    },
    {
      icon: Clock,
      label: 'Heures d\'absence',
      value: `${stats?.total_absence_hours ?? 0}h`,
      color: 'bg-red-600/20 text-red-300',
    },
    {
      icon: AlertCircle,
      label: 'Absences',
      value: stats?.absences ?? stats?.absent_count ?? 0,
      color: 'bg-amber-600/20 text-amber-300',
    },
  ];

  return (
    <RoleGuard allow={['student']}>
      <div className="mx-auto max-w-7xl p-6">
        <OnboardingWalkthrough />
        <Breadcrumbs items={[{ label: 'Mon espace étudiant' }]} />
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-white dark:text-white light:text-gray-900">
            Mon tableau de bord
          </h1>
          <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600">
            Suivi de votre présence et de vos classes.
          </p>
        </div>

        {/* ⭐ VISUAL ALERT LEVEL INDICATOR */}
        {stats?.alert_level && stats.alert_level !== 'none' && (
          <Alert
            className={`mb-4 ${
              stats.alert_level === 'failing'
                ? 'border-red-500/50 bg-red-600/20'
                : stats.alert_level === 'critical'
                ? 'border-orange-500/50 bg-orange-600/20'
                : 'border-yellow-500/50 bg-yellow-600/20'
            }`}
          >
            <AlertCircle
              className={`h-4 w-4 ${
                stats.alert_level === 'failing'
                  ? 'text-red-400'
                  : stats.alert_level === 'critical'
                  ? 'text-orange-400'
                  : 'text-yellow-400'
              }`}
            />
            <AlertDescription
              className={`${
                stats.alert_level === 'failing'
                  ? 'text-red-300'
                  : stats.alert_level === 'critical'
                  ? 'text-orange-300'
                  : 'text-yellow-300'
              }`}
            >
              {stats.alert_level === 'failing' && (
                <>
                  <strong>Alerte critique:</strong> Votre taux de présence ({stats.attendance_rate.toFixed(1)}%) est
                  en dessous du seuil acceptable. Contactez votre formateur immédiatement.
                </>
              )}
              {stats.alert_level === 'critical' && (
                <>
                  <strong>Attention:</strong> Votre taux de présence ({stats.attendance_rate.toFixed(1)}%)
                  nécessite une amélioration urgente.
                </>
              )}
              {stats.alert_level === 'warning' && (
                <>
                  <strong>Avertissement:</strong> Votre taux de présence ({stats.attendance_rate.toFixed(1)}%) est en
                  baisse. Soyez plus assidu.
                </>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* AI Attendance Score Card (if available from N8N) */}
        {stats?.ai_score !== null && stats?.ai_score !== undefined && (
          <div className="mb-4 rounded-xl border border-purple-500/30 bg-gradient-to-br from-purple-600/20 to-pink-600/20 p-6">
            <div className="flex items-start gap-4">
              <div className="rounded-full bg-purple-500/20 p-3">
                <TrendingUp className="h-6 w-6 text-purple-300" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold text-white">Score d'Assiduité IA</h3>
                  <span className={`text-3xl font-bold ${
                    stats.ai_score >= 80 ? 'text-emerald-400' :
                    stats.ai_score >= 60 ? 'text-amber-400' :
                    'text-red-400'
                  }`}>
                    {stats.ai_score}/100
                  </span>
                </div>
                {stats.ai_explanation && (
                  <p className="text-sm text-purple-200 leading-relaxed">
                    {stats.ai_explanation}
                  </p>
                )}
                <div className="mt-3 h-2 w-full rounded-full bg-white/10 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      stats.ai_score >= 80 ? 'bg-emerald-500' :
                      stats.ai_score >= 60 ? 'bg-amber-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${stats.ai_score}%` }}
                  />
                </div>
                <p className="text-xs text-purple-300/70 mt-2">
                  Calculé automatiquement par IA basé sur vos absences et présences
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-4 mb-6">
          {cards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <div
                key={idx}
                className={`rounded-lg border border-white/10 ${card.color} p-4 dark:border-white/10 light:border-gray-200 light:bg-gray-50`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium opacity-75">{card.label}</p>
                    <p className="text-2xl font-bold mt-1">{card.value}</p>
                  </div>
                  <Icon className="h-5 w-5 opacity-50" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Facial Recognition Check-in CTA */}
        <Link
          href="/student/check-in"
          className="block rounded-xl border-2 border-emerald-500/30 bg-gradient-to-r from-emerald-600/20 to-blue-600/20 p-6 hover:border-emerald-500/50 transition group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="rounded-full bg-emerald-500/20 p-4 group-hover:bg-emerald-500/30 transition">
                <Camera className="h-8 w-8 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white mb-1">
                  Check-in par Reconnaissance Faciale
                </h3>
                <p className="text-sm text-zinc-300">
                  Pointez votre présence avec votre visage pour les sessions actives
                </p>
              </div>
            </div>
            <ChevronRight className="h-6 w-6 text-emerald-400 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Upcoming Sessions */}
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white dark:text-white light:text-gray-900">
                Prochains cours
              </h2>
              <Link
                href="/student/schedule"
                className="text-xs text-amber-400 hover:text-amber-300"
              >
                Voir plus →
              </Link>
            </div>
            {upcomingSessions && upcomingSessions.length > 0 ? (
              <div className="space-y-3">
                {upcomingSessions.slice(0, 3).map((session) => (
                  <div
                    key={session.id}
                    className="flex items-start justify-between rounded-lg border border-white/10 bg-white/2 p-3 dark:border-white/10 dark:bg-white/2 light:border-gray-200 light:bg-gray-50"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-white dark:text-white light:text-gray-900 truncate">
                        {session.subject}
                      </p>
                      <p className="text-xs text-zinc-400 dark:text-zinc-400 light:text-gray-600">
                        {session.date} • {session.time}
                      </p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-500 light:text-gray-500 mt-1">
                        {session.classroom} • {session.trainer_name}
                      </p>
                    </div>
                    <Calendar className="h-4 w-4 text-zinc-400 flex-shrink-0 mt-1" />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600">
                Aucun cours prévu
              </p>
            )}
          </div>

          {/* Recent Attendance */}
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white dark:text-white light:text-gray-900">
                Historique de présence
              </h2>
              <Link
                href="/student/attendance"
                className="text-xs text-amber-400 hover:text-amber-300"
              >
                Voir plus →
              </Link>
            </div>
            {attendance && attendance.length > 0 ? (
              <div className="space-y-2">
                {attendance.slice(0, 4).map((record) => (
                  <div
                    key={record.id}
                    className="flex items-center justify-between rounded-lg border border-white/10 bg-white/2 p-3 dark:border-white/10 dark:bg-white/2 light:border-gray-200 light:bg-gray-50"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      {getStatusIcon(record.status)}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-white dark:text-white light:text-gray-900 truncate">
                          {record.subject}
                        </p>
                        <p className="text-xs text-zinc-400 dark:text-zinc-400 light:text-gray-600">
                          {record.date}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${getStatusColor(record.status)}`}
                    >
                      {getStatusLabel(record.status)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600">
                Aucun enregistrement
              </p>
            )}
          </div>
        </div>

        {/* Action Cards */}
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6 mt-6">
          <Link
            href="/student/justification"
            className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white hover:bg-white/10 dark:hover:bg-white/10 light:hover:bg-gray-50 transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white dark:text-white light:text-gray-900">
                  Justifier une absence
                </h3>
                <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600 mt-1">
                  Soumettez une justification pour vos absences
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-zinc-400" />
            </div>
          </Link>

          <Link
            href="/student/feedback"
            className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white hover:bg-white/10 dark:hover:bg-white/10 light:hover:bg-gray-50 transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white dark:text-white light:text-gray-900">
                  Partager un feedback
                </h3>
                <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600 mt-1">
                  Soumettez vos suggestions et suivez les réponses
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-zinc-400" />
            </div>
          </Link>

          <Link
            href="/student/notifications"
            className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white hover:bg-white/10 dark:hover:bg-white/10 light:hover:bg-gray-50 transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white dark:text-white light:text-gray-900">
                  Notifications & alertes
                </h3>
                <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600 mt-1">
                  Consultez vos alertes et ajustez vos préférences
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-zinc-400" />
            </div>
          </Link>

          <Link
            href="/student/profile"
            className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white hover:bg-white/10 dark:hover:bg-white/10 light:hover:bg-gray-50 transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white dark:text-white light:text-gray-900">
                  Mon profil
                </h3>
                <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600 mt-1">
                  Mettez à jour vos informations et préférences
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-zinc-400" />
            </div>
          </Link>

          <Link
            href="/student/calendar"
            className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white hover:bg-white/10 dark:hover:bg-white/10 light:hover:bg-gray-50 transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white dark:text-white light:text-gray-900">
                  Calendrier unifié
                </h3>
                <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600 mt-1">
                  Retrouvez vos cours, examens et rappels
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-zinc-400" />
            </div>
          </Link>

          <Link
            href="/student/schedule"
            className="rounded-xl border border-white/10 bg-white/5 p-6 dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white hover:bg-white/10 dark:hover:bg-white/10 light:hover:bg-gray-50 transition"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white dark:text-white light:text-gray-900">
                  Mon emploi du temps
                </h3>
                <p className="text-sm text-zinc-400 dark:text-zinc-400 light:text-gray-600 mt-1">
                  Consultez vos cours et vos horaires
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-zinc-400" />
            </div>
          </Link>
        </div>
      </div>
    </RoleGuard>
  );
}
