/**
 * Global command palette for quick navigation and actions.
 * Press Cmd+K (Mac) or Ctrl+K (Windows/Linux) to open.
 */
'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Users,
  GraduationCap,
  Calendar,
  BarChart3,
  Settings,
  MessageSquare,
  Camera,
  FileText,
  Bell,
  LogOut,
  Command,
  Loader2,
} from 'lucide-react';
import axios from 'axios';
import { getApiBase } from '@/lib/config';
import { useAuth } from '@/lib/auth-context';

type CommandItem = {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
  keywords?: string[];
  category?: string;
};

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [remoteResults, setRemoteResults] = useState<CommandItem[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const apiBase = getApiBase();
  const { user, logout } = useAuth();

  // Keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const commands: CommandItem[] = useMemo(() => {
    const role = user?.role;
    const items: CommandItem[] = [];

    // NTIC2 assistant entry
    items.push({
      id: 'nav-assistant',
      label: 'Assistant NTIC2',
      icon: <MessageSquare className="h-4 w-4" />,
      action: () => router.push('/assistant'),
      keywords: ['assistant', 'chatbot', 'ai', 'help', 'ntic2'],
      category: 'Navigation',
    });

    if (role === 'admin') {
      items.push(
        {
          id: 'nav-trainers',
          label: 'Formateurs',
          icon: <Users className="h-4 w-4" />,
          action: () => router.push('/admin/trainers'),
          keywords: ['trainers', 'formateurs', 'teachers'],
          category: 'Navigation',
        },
        {
          id: 'nav-students',
          label: 'Étudiants',
          icon: <GraduationCap className="h-4 w-4" />,
          action: () => router.push('/admin/students'),
          keywords: ['students', 'étudiants', 'pupils'],
          category: 'Navigation',
        },
        {
          id: 'nav-faces',
          label: 'Enrôlement facial',
          icon: <Camera className="h-4 w-4" />,
          action: () => router.push('/admin/faces'),
          keywords: ['faces', 'facial', 'biometric', 'enroll'],
          category: 'Navigation',
        },
        {
          id: 'nav-users',
          label: 'Créer un utilisateur',
          icon: <Users className="h-4 w-4" />,
          action: () => router.push('/admin/users'),
          keywords: ['users', 'create', 'account'],
          category: 'Navigation',
        },
        {
          id: 'nav-sessions',
          label: 'Sessions',
          icon: <Calendar className="h-4 w-4" />,
          action: () => router.push('/admin/sessions'),
          keywords: ['sessions', 'classes', 'schedule'],
          category: 'Navigation',
        },
        {
          id: 'nav-analytics',
          label: 'Analytique',
          icon: <BarChart3 className="h-4 w-4" />,
          action: () => router.push('/admin/analytics'),
          keywords: ['analytics', 'stats', 'reports'],
          category: 'Navigation',
        },
        {
          id: 'nav-notifications',
          label: 'Notifications',
          icon: <Bell className="h-4 w-4" />,
          action: () => router.push('/admin/notifications'),
          keywords: ['notifications', 'alerts'],
          category: 'Navigation',
        },
      );
    }

    if (role === 'trainer') {
      items.push(
        {
          id: 'nav-trainer-sessions',
          label: 'Mes sessions',
          icon: <Calendar className="h-4 w-4" />,
          action: () => router.push('/trainer/sessions'),
          keywords: ['sessions', 'cours'],
          category: 'Navigation',
        },
        {
          id: 'nav-trainer-attendance',
          label: 'Présences',
          icon: <FileText className="h-4 w-4" />,
          action: () => router.push('/trainer/attendance'),
          keywords: ['attendance', 'présences'],
          category: 'Navigation',
        },
      );
    }

    if (role === 'student') {
      items.push(
        {
          id: 'nav-student-schedule',
          label: 'Emploi du temps',
          icon: <Calendar className="h-4 w-4" />,
          action: () => router.push('/student/schedule'),
          keywords: ['schedule', 'emploi du temps'],
          category: 'Navigation',
        },
        {
          id: 'nav-student-attendance',
          label: 'Mes présences',
          icon: <FileText className="h-4 w-4" />,
          action: () => router.push('/student/attendance'),
          keywords: ['attendance', 'présences'],
          category: 'Navigation',
        },
      );
    }

    items.push({
      id: 'action-logout',
      label: 'Se déconnecter',
      icon: <LogOut className="h-4 w-4" />,
      action: () => logout(),
      keywords: ['logout', 'sign out', 'disconnect'],
      category: 'Actions',
    });

    return items;
  }, [logout, router, user?.role]);

  const filteredCommands = useMemo(() => {
    if (!search) return [...commands, ...remoteResults];

    const lowerSearch = search.toLowerCase();
    return [...commands, ...remoteResults].filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(lowerSearch) ||
        cmd.keywords?.some((kw) => kw.toLowerCase().includes(lowerSearch)),
    );
  }, [search, commands, remoteResults]);

  const fetchRemote = useCallback(
    async (term: string) => {
      // Remote search is admin-only.
      if (user?.role !== 'admin') {
        setRemoteResults([]);
        return;
      }
      if (!term || term.length < 2) {
        setRemoteResults([]);
        return;
      }
      setLoading(true);
      try {
        const res = await axios.get(
          `${apiBase}/api/admin/search?q=${encodeURIComponent(term)}&limit=12`,
        );
        const items = (res.data?.items || []).map((item: any) => ({
          id: `${item.entity}-${item.id}`,
          label: item.title,
          icon: <Search className="h-4 w-4" />,
          action: () => {
            if (item.entity === 'student') router.push(`/admin/students?focus=${item.id}`);
            if (item.entity === 'trainer') router.push(`/admin/trainers?focus=${item.id}`);
            if (item.entity === 'session') router.push(`/admin/sessions?focus=${item.id}`);
          },
          keywords: [item.subtitle || '', item.entity],
          category: 'Recherche',
        }));
        setRemoteResults(items);
      } catch {
        setRemoteResults([]);
      } finally {
        setLoading(false);
      }
    },
    [apiBase, router, user?.role],
  );

  // Debounce remote search
  useEffect(() => {
    const id = setTimeout(() => fetchRemote(search), 200);
    return () => clearTimeout(id);
  }, [search, fetchRemote]);

  const handleSelect = (command: CommandItem) => {
    command.action();
    setIsOpen(false);
    setSearch('');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />

          {/* Command Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed left-1/2 top-[20%] z-[201] w-full max-w-2xl -translate-x-1/2 overflow-hidden rounded-xl border border-white/10 bg-zinc-900 shadow-2xl"
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
              <Search className="h-5 w-5 text-zinc-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher une page, action ou fonctionnalité..."
                className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-500 outline-none"
                autoFocus
              />
              <div className="flex items-center gap-1 rounded border border-white/20 px-2 py-1 text-xs text-zinc-400">
                {loading ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Command className="h-3 w-3" />
                )}
                K
              </div>
            </div>

            {/* Results */}
            <div className="max-h-96 overflow-y-auto">
              {filteredCommands.length === 0 ? (
                <div className="px-4 py-12 text-center text-sm text-zinc-500">
                  Aucun résultat trouvé
                </div>
              ) : (
                <div>
                  {Object.entries(
                    filteredCommands.reduce(
                      (acc, cmd) => {
                        const cat = cmd.category || 'Autre';
                        if (!acc[cat]) acc[cat] = [];
                        acc[cat].push(cmd);
                        return acc;
                      },
                      {} as Record<string, CommandItem[]>,
                    ),
                  ).map(([category, items]) => (
                    <div key={category}>
                      <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                        {category}
                      </div>
                      {items.map((cmd) => (
                        <button
                          key={cmd.id}
                          onClick={() => handleSelect(cmd)}
                          className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/5"
                        >
                          <div className="text-amber-400">{cmd.icon}</div>
                          <span className="flex-1 text-sm text-white">{cmd.label}</span>
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t border-white/10 px-4 py-2 text-xs text-zinc-500">
              <span>Utilisez ↑↓ pour naviguer</span>
              <span>Entrée pour sélectionner</span>
              <span>Échap pour fermer</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
