'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useProfile, useUpdateProfile } from '../hooks/useSettings';

export function ProfileSection() {
  const t = useTranslations('Settings');
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();

  const [displayName, setDisplayName] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  if (isLoading) {
    return (
      <section className="cyber-card p-6 animate-pulse">
        <div className="h-6 bg-grid-line/30 rounded w-1/4 mb-4" />
        <div className="h-4 bg-grid-line/20 rounded w-1/2" />
      </section>
    );
  }

  const handleSave = () => {
    updateProfile.mutate({ display_name: displayName }, {
      onSuccess: () => setIsEditing(false),
    });
  };

  return (
    <section>
      <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
        {t('profile') || 'Profile'}
      </h2>

      <div className="cyber-card p-6 space-y-4">
        <div>
          <label className="text-sm text-muted-foreground uppercase">{t('email') || 'Email'}</label>
          <p className="font-mono mt-1">{profile?.email}</p>
        </div>

        <div>
          <label className="text-sm text-muted-foreground uppercase">{t('displayName') || 'Display Name'}</label>
          {isEditing ? (
            <div className="flex gap-2 mt-1">
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="flex-1 bg-terminal-surface border border-grid-line/30 rounded px-3 py-2 font-mono text-sm"
                placeholder={profile?.display_name || ''}
              />
              <button onClick={handleSave} className="px-4 py-2 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors">
                {t('save') || 'Save'}
              </button>
              <button onClick={() => setIsEditing(false)} className="px-4 py-2 bg-muted/20 hover:bg-muted/30 border border-muted/50 text-muted-foreground font-mono text-sm rounded transition-colors">
                {t('cancel') || 'Cancel'}
              </button>
            </div>
          ) : (
            <div className="flex justify-between items-center mt-1">
              <p className="font-mono">{profile?.display_name}</p>
              <button onClick={() => { setDisplayName(profile?.display_name || ''); setIsEditing(true); }} className="text-xs text-neon-cyan hover:text-neon-cyan/80 font-mono">
                {t('edit') || 'Edit'}
              </button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-grid-line/30">
          <div>
            <label className="text-sm text-muted-foreground uppercase">{t('language') || 'Language'}</label>
            <p className="font-mono text-sm mt-1">{profile?.language}</p>
          </div>
          <div>
            <label className="text-sm text-muted-foreground uppercase">{t('timezone') || 'Timezone'}</label>
            <p className="font-mono text-sm mt-1">{profile?.timezone}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
