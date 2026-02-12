'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { invitesApi } from '@/lib/api/invites';
import { promoApi } from '@/lib/api/promo';
import { CyberInput } from '@/features/auth/components/CyberInput';
import { motion } from 'motion/react';
import { Gift, Tag, Check, Copy, CheckCircle, Percent } from 'lucide-react';
import { AxiosError } from 'axios';

interface InviteCode {
  code: string;
  expires_at?: string | null;
  uses_remaining?: number;
}

interface PromoDiscount {
  discount_percent?: number;
  discount_amount?: number;
  expires_at?: string;
}

export function CodesSection() {
  // Invite code state
  const [inviteCode, setInviteCode] = useState('');
  const [redeemingInvite, setRedeemingInvite] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');

  // Promo code state
  const [promoCode, setPromoCode] = useState('');
  const [validatingPromo, setValidatingPromo] = useState(false);
  const [promoError, setPromoError] = useState('');
  const [promoDiscount, setPromoDiscount] = useState<PromoDiscount | null>(null);

  // Fetch user's invite codes
  const { data: myInvites, isLoading: loadingInvites } = useQuery({
    queryKey: ['my-invites'],
    queryFn: async () => {
      const response = await invitesApi.getMyInvites();
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  // Handle invite code redemption
  const handleRedeemInvite = async () => {
    if (!inviteCode.trim()) {
      setInviteError('Please enter an invite code');
      return;
    }

    setRedeemingInvite(true);
    setInviteError('');
    setInviteSuccess('');

    try {
      await invitesApi.redeem({ code: inviteCode });
      setInviteSuccess('Invite code redeemed successfully!');
      setInviteCode('');

      // Refetch user invites after redemption
      setTimeout(() => {
        window.location.reload(); // Simple reload to show updated data
      }, 2000);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 404) {
          setInviteError('Invalid or expired invite code');
        } else if (err.response?.status === 400) {
          setInviteError(detail || 'Code already redeemed or invalid');
        } else {
          setInviteError(detail || 'Failed to redeem invite code');
        }
      } else {
        setInviteError('An error occurred. Please try again.');
      }
    } finally {
      setRedeemingInvite(false);
    }
  };

  // Handle promo code validation
  const handleValidatePromo = async () => {
    if (!promoCode.trim()) {
      setPromoError('Please enter a promo code');
      return;
    }

    setValidatingPromo(true);
    setPromoError('');
    setPromoDiscount(null);

    try {
      const response = await promoApi.validate({ code: promoCode });
      setPromoDiscount(response.data);
    } catch (err) {
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 404) {
          setPromoError('Invalid or expired promo code');
        } else if (err.response?.status === 400) {
          setPromoError(detail || 'Promo code not valid');
        } else {
          setPromoError(detail || 'Failed to validate promo code');
        }
      } else {
        setPromoError('An error occurred. Please try again.');
      }
    } finally {
      setValidatingPromo(false);
    }
  };

  // Copy code to clipboard
  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      console.error('Failed to copy code');
    }
  };

  return (
    <div className="space-y-6">
      {/* Invite Code Redemption */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="cyber-card p-6"
      >
        <div className="flex items-start gap-4 mb-4">
          <div className="p-3 bg-neon-pink/10 border border-neon-pink/30 rounded-lg">
            <Gift className="h-6 w-6 text-neon-pink" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-display text-neon-pink mb-1">
              Redeem Invite Code
            </h3>
            <p className="text-sm text-muted-foreground">
              Have an invite code? Redeem it to unlock rewards
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <CyberInput
            label="Invite Code"
            type="text"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
            placeholder="CYBER2024"
            prefix="invite"
            error={inviteError}
            disabled={redeemingInvite}
            onKeyDown={(e) => e.key === 'Enter' && handleRedeemInvite()}
          />

          {inviteSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 p-3 bg-matrix-green/10 border border-matrix-green/30 rounded text-matrix-green text-sm font-mono"
            >
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
              <span>{inviteSuccess}</span>
            </motion.div>
          )}

          <button
            onClick={handleRedeemInvite}
            disabled={redeemingInvite || !inviteCode.trim()}
            className="w-full px-4 py-3 bg-neon-pink/20 hover:bg-neon-pink/30 border border-neon-pink/50 text-neon-pink font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {redeemingInvite ? 'Redeeming...' : 'Redeem Code'}
          </button>
        </div>
      </motion.div>

      {/* My Invite Codes */}
      {myInvites && myInvites.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="cyber-card p-6"
        >
          <h3 className="text-lg font-display text-neon-cyan mb-4">
            My Invite Codes
          </h3>

          {loadingInvites ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="p-3 bg-terminal-bg border border-grid-line/30 rounded animate-pulse">
                  <div className="h-4 bg-grid-line/20 rounded w-1/3" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {myInvites.map((invite: InviteCode, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-3 bg-terminal-bg border border-grid-line/30 rounded hover:border-neon-cyan/50 transition-colors"
                >
                  <div>
                    <code className="text-sm font-mono text-neon-cyan">
                      {invite.code}
                    </code>
                    {invite.expires_at && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Expires: {new Date(invite.expires_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => copyCode(invite.code)}
                    className="p-2 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan rounded transition-colors"
                    aria-label="Copy code"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* Promo Code Validation */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="cyber-card p-6"
      >
        <div className="flex items-start gap-4 mb-4">
          <div className="p-3 bg-neon-purple/10 border border-neon-purple/30 rounded-lg">
            <Tag className="h-6 w-6 text-neon-purple" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-display text-neon-purple mb-1">
              Validate Promo Code
            </h3>
            <p className="text-sm text-muted-foreground">
              Check your promo code for available discounts
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <CyberInput
            label="Promo Code"
            type="text"
            value={promoCode}
            onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
            placeholder="SAVE20"
            prefix="promo"
            error={promoError}
            disabled={validatingPromo}
            onKeyDown={(e) => e.key === 'Enter' && handleValidatePromo()}
          />

          {/* Discount Preview */}
          {promoDiscount && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-4 bg-matrix-green/10 border border-matrix-green/30 rounded-lg"
            >
              <div className="flex items-start gap-3">
                <Percent className="h-5 w-5 text-matrix-green flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Check className="h-4 w-4 text-matrix-green" />
                    <span className="text-sm font-semibold text-matrix-green">
                      Valid Promo Code
                    </span>
                  </div>

                  <div className="space-y-1 text-sm text-muted-foreground">
                    {promoDiscount.discount_percent && (
                      <p>Discount: <span className="text-matrix-green font-mono">{promoDiscount.discount_percent}%</span></p>
                    )}
                    {promoDiscount.discount_amount && (
                      <p>Discount: <span className="text-matrix-green font-mono">${promoDiscount.discount_amount}</span></p>
                    )}
                    {promoDiscount.expires_at && (
                      <p className="text-xs">
                        Valid until: {new Date(promoDiscount.expires_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          <button
            onClick={handleValidatePromo}
            disabled={validatingPromo || !promoCode.trim()}
            className="w-full px-4 py-3 bg-neon-purple/20 hover:bg-neon-purple/30 border border-neon-purple/50 text-neon-purple font-mono text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {validatingPromo ? 'Validating...' : 'Validate Promo'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
