'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { LogOut, Home, Users, UserCheck, GraduationCap, Menu, X, Bot } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import UserProfileMenu from './UserProfileMenu';
import { NotificationBell } from '../NotificationBell';
import LanguageSwitcher from './LanguageSwitcher';

export default function RoleNavBar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!user) return null;

  const links = [
    { href: '/', label: 'Accueil', icon: Home, roles: ['admin', 'trainer', 'student'] },
    { href: '/assistant', label: 'Assistant NTIC2', icon: Bot, roles: ['admin', 'trainer', 'student'] },
    { href: '/admin', label: 'Admin', icon: Users, roles: ['admin'] },
    { href: '/trainer', label: 'Formateur', icon: UserCheck, roles: ['trainer'] },
    { href: '/student', label: 'Étudiant', icon: GraduationCap, roles: ['student'] },
  ];

  const availableLinks = links.filter((link) => link.roles.includes(user.role));

  return (
    <nav
      className="sticky top-0 z-50 border-b border-white/10 bg-white/5 backdrop-blur-xl dark:border-white/10 dark:bg-white/5 light:border-gray-200 light:bg-white"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-600">
            <span className="text-sm font-bold text-white" aria-hidden="true">
              SP
            </span>
          </div>
          <span className="hidden text-sm font-semibold text-white sm:inline dark:text-white light:text-gray-900">
            Smart Presence AI
          </span>
        </div>

        {/* Desktop Navigation */}
        <div className="hidden items-center gap-1 md:flex">
          {availableLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href || pathname.startsWith(link.href + '/');
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-amber-600/20 text-amber-400'
                    : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 light:text-gray-600 light:hover:bg-gray-100 light:hover:text-gray-900'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {link.label}
              </Link>
            );
          })}
        </div>

        {/* Desktop Actions */}
        <div className="hidden items-center gap-3 md:flex">
          <NotificationBell />
            <LanguageSwitcher />
            <ThemeToggle />
          <UserProfileMenu />
        </div>

        {/* Mobile Menu Button */}
        <div className="flex items-center gap-2 md:hidden">
          <NotificationBell />
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-amber-600 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white light:text-gray-600 light:hover:bg-gray-100 light:hover:text-gray-900"
            aria-label={mobileMenuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
          >
            {mobileMenuOpen ? (
              <X className="h-6 w-6" aria-hidden="true" />
            ) : (
              <Menu className="h-6 w-6" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
      {/* Secondary section links per role */}
      <div className="mx-auto max-w-7xl px-4 pb-3">
        {user.role === 'admin' && (
          <div className="flex flex-wrap gap-2">
            {[
              { href: '/admin/users', label: 'Utilisateurs' },
              { href: '/admin/faces', label: 'Visages' },
              { href: '/admin/students', label: 'Étudiants' },
              { href: '/admin/trainers', label: 'Formateurs' },
              { href: '/admin/sessions', label: 'Sessions' },
              { href: '/admin/import', label: 'Import' },
              { href: '/admin/notifications', label: 'Notifications' },
              { href: '/admin/analytics', label: 'Analytique' },
              { href: '/admin/reports', label: 'Rapports PDF' },
            ].map((l) => {
              const isActive = pathname === l.href || pathname.startsWith(l.href + '/');
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${isActive ? 'bg-amber-600/30 text-amber-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 light:text-gray-600 light:hover:bg-gray-100 light:hover:text-gray-900'}`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
        )}
        {user.role === 'trainer' && (
          <div className="flex flex-wrap gap-2">
            {[
              { href: '/trainer', label: 'Tableau de bord' },
              { href: '/trainer/attendance', label: 'Présences' },
              { href: '/trainer/mark-attendance', label: 'Pointage' },
              { href: '/trainer/sessions', label: 'Sessions' },
            ].map((l) => {
              const isActive = pathname === l.href || pathname.startsWith(l.href + '/');
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${isActive ? 'bg-blue-600/30 text-blue-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 light:text-gray-600 light:hover:bg-gray-100 light:hover:text-gray-900'}`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
        )}
        {user.role === 'student' && (
          <div className="flex flex-wrap gap-2">
            {[
              { href: '/student', label: 'Tableau de bord' },
              { href: '/student/schedule', label: 'Emploi du temps' },
              { href: '/student/justification', label: 'Justifications' },
            ].map((l) => {
              const isActive = pathname === l.href || pathname.startsWith(l.href + '/');
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${isActive ? 'bg-emerald-600/30 text-emerald-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 light:text-gray-600 light:hover:bg-gray-100 light:hover:text-gray-900'}`}
                >
                  {l.label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div
          className="border-t border-zinc-800 dark:border-zinc-800 light:border-gray-200 md:hidden"
        >
          <div className="space-y-1 px-4 py-3">
            {availableLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href || pathname.startsWith(link.href + '/');
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-amber-600/20 text-amber-400'
                      : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200 light:text-gray-600 light:hover:bg-gray-100 light:hover:text-gray-900'
                  }`}
                  onClick={() => setMobileMenuOpen(false)}
                  role="menuitem"
                  aria-current={isActive ? 'page' : undefined}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                  {link.label}
                </Link>
              );
            })}
            <div className="border-t border-zinc-800 pt-3 dark:border-zinc-800 light:border-gray-200">
              <div className="mb-3 flex items-center gap-2 px-3">
                <ThemeToggle />
              </div>
              <div className="md:hidden">
                <UserProfileMenu />
              </div>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
